import openai
from approaches.approach import Approach
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType
from langchain.llms.openai import AzureOpenAI
from langchain.callbacks.manager import CallbackManager, Callbacks
from langchain.chains import LLMChain, RetrievalQAWithSourcesChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory, ConversationSummaryBufferMemory
from langchain.agents import Tool, AgentExecutor, initialize_agent, AgentType, ConversationalAgent
from langchain.llms.openai import AzureOpenAI
from langchainadapters import HtmlCallbackHandler
from vdbutils.retriever import Retriever, SearchModes
# from langchain.retrievers import AzureCognitiveSearchRetriever  # Does not support vector
from langchain.prompts import PromptTemplate, BasePromptTemplate
from langchain.chains.qa_with_sources.loading import load_qa_with_sources_chain
from .templates import combine_prompt_template, document_prompt_template, main_prompt_template_prefix, main_prompt_template_suffix


# Attempt to answer questions by first composing a full query based on history and last user question, then retrieving
# a few most relevant information from KB, then fomulates a final answer based on the information.
# Uses ConversationalReactAgent to determine which tool to use and keeping memory
class ChatConversationalReadRetrieveReadApproach(Approach):

    def __init__(self, search_client: SearchClient, chatgpt_deployment: str, gpt_deployment: str, embedding_deployment: str, source_field: str, content_field: str):
        self.chatgpt_deployment = chatgpt_deployment
        self.gpt_deployment = gpt_deployment
        self.source_field = source_field
        self.content_field = content_field
        self.search_client = search_client
        self.embedding_deployment = embedding_deployment
        
    def run(self, q: str, overrides: dict) -> any:

        # Use to capture thought process during iterations
        cb_handler = HtmlCallbackHandler()
        cb_manager = CallbackManager(handlers=[cb_handler])

        bmo_search_tool = BMOSearchTool(overrides, self.search_client, self.gpt_deployment, self.embedding_deployment, cb_manager)
        tools = [
            bmo_search_tool

            # Tool(name="OtherQuestions",
            #     func=lambda q:q,
            #     description="MUST use this tool when the question asks for information on other banks, organizaions, " \
            #                 "or individual such as HSBC, TD, RBC, or if user asks math questions such as \"what is 1+1\"",
            #     return_direct=True
            # )
        ]

        llm = AzureOpenAI(deployment_name=self.gpt_deployment, temperature=0, openai_api_key=openai.api_key)
        # memory = ConversationBufferWindowMemory(
        memory = ConversationSummaryBufferMemory(
            memory_key="chat_history",  # important to align with agent prompt (below)
            k=5,
            return_messages=True,
            llm=llm
        )

        llm_chat = AzureOpenAI(deployment_name=self.chatgpt_deployment, temperature=overrides.get("temperature") or 0.3, openai_api_key=openai.api_key)

        prompt = ConversationalAgent.create_prompt(
            tools=tools,
            prefix=overrides.get("prompt_template_prefix") or main_prompt_template_prefix,
            suffix=overrides.get("prompt_template_prefix") or main_prompt_template_suffix,  # Must align memory_key (above)
            input_variables = ["input", "agent_scratchpad"]
        )

        chain = LLMChain(llm=llm_chat, prompt=prompt)
        executor = AgentExecutor.from_agent_and_tools(
            agent=ConversationalAgent(llm_chain = chain, tools = tools),
            tools=tools,
            verbose=True,
            memory=memory,
            early_stopping_method="generate",
            return_only_outputs=True,
            callback_manager=cb_manager
        )
        result = executor.run(q)

        # Remove references to tool names that might be confused with a citation
        result = result.replace("[BMOSearch]", "").replace("[OtherQuestions]", "")

        return {"data_points": bmo_search_tool.last_sources or [], "answer": result, "thoughts": cb_handler.get_and_reset_log()}


class BMOSearchTool(Tool):
    def __init__(self, overrides, search_client: SearchClient, gpt_deployment: str, embedding_deployment: str, callbacks: Callbacks = None):
        super().__init__(name="BMOSearch",
                         description="useful for answering questions about the employee, their insurances, benefits and other personal information",
                         callbacks=callbacks)
        self.func = lambda q: self.bmo_search(q, overrides)
        self.last_sources = None
        self.search_client = search_client
        self.gpt_deployment = gpt_deployment
        self.embedding_deployment = embedding_deployment

    def bmo_search(self, q, overrides):
        exclude_category = overrides.get("exclude_category") or None
        search_kwargs = dict(
            mode=overrides.get("mode") or SearchModes.Vector,
            use_semantic_captions=True if overrides.get("semantic_captions") else False,
            filter="category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None,
            top=overrides.get("top") or 3,
            k=overrides.get("vector_search_k") or 3
        )

        llm_search = AzureOpenAI(deployment_name=self.gpt_deployment, temperature=0, openai_api_key=openai.api_key)
        prompt = PromptTemplate(template=combine_prompt_template,
                                input_variables=["summaries", "question"])
        document_prompt = PromptTemplate(template=document_prompt_template,
                                         input_variables=["page_content", "source"])

        qa_chain = load_qa_with_sources_chain(llm_search, chain_type="stuff",
                                              prompt=prompt,
                                              document_prompt=document_prompt)
        retriever = Retriever(search_client=self.search_client,
                              embedding_deployment=self.embedding_deployment,
                              search_kwargs=search_kwargs)
        chain = RetrievalQAWithSourcesChain(combine_documents_chain=qa_chain, retriever=retriever,
                                            reduce_k_below_max_tokens=True, max_tokens_limit=3000,
                                            return_source_documents=True)

        result = chain.run(q)
        self.last_sources = retriever.last_sources
        return result
