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
from typing import Any, Dict, List, Optional, Union
from langchain.schema import HumanMessage, AIMessage
from langchain.agents.conversational.output_parser import ConvoOutputParser
from langchain.schema import AgentAction, AgentFinish, OutputParserException
import re


class EarlyStopConvoOutputParser(ConvoOutputParser):
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        if f"{self.ai_prefix}:" in text:
            return AgentFinish(
                {"output": text.split(f"{self.ai_prefix}:")[-1].split('New input', 1)[0].strip()}, text
            )
        regex = r"Action: (.*?)[\n]*Action Input: (.*)"
        match = re.search(regex, text)
        if not match:
            raise OutputParserException(f"Could not parse LLM output: `{text}`")
        action = match.group(1)
        action_input = match.group(2)
        return AgentAction(action.strip(), action_input.strip(" ").strip('"'), text)


class StatelessAgentExecutor(AgentExecutor):
    def prep_outputs(self,
                     inputs: Dict[str, str],
                     outputs: Dict[str, str],
                     return_only_outputs: bool = False,
    ) -> Dict[str, str]:
        """Validate and prep outputs."""
        self._validate_outputs(outputs)
        return outputs if return_only_outputs else {**inputs, **outputs}


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
        self.last_sources = None

    def bmo_search(self, q, overrides):
        exclude_category = overrides.get("exclude_category") or None
        search_kwargs = dict(
            mode=overrides.get("mode") or SearchModes.Vector,
            use_semantic_captions=True if overrides.get("semantic_captions") else False,
            filter="category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None,
            top=overrides.get("top") or 3,
            vector_search_k=overrides.get("vector_search_k") or 3
        )

        llm_search = AzureOpenAI(deployment_name=self.gpt_deployment, temperature=0, openai_api_key=openai.api_key)
        prompt = PromptTemplate(template=combine_prompt_template,
                                input_variables=["summaries", "question"])
        document_prompt = PromptTemplate(template=document_prompt_template,
                                         input_variables=["page_content", "source"])

        retriever = Retriever(search_client=self.search_client,
                              embedding_deployment=self.embedding_deployment,
                              search_kwargs=search_kwargs)

        # This chain combine retrieved sources to knowledge summaries
        qa_chain = load_qa_with_sources_chain(llm_search, chain_type="stuff",
                                              prompt=prompt,
                                              document_prompt=document_prompt)
        chain = RetrievalQAWithSourcesChain(combine_documents_chain=qa_chain, retriever=retriever,
                                            reduce_k_below_max_tokens=True, max_tokens_limit=3000)
                                            # return_source_documents=True)

        # result = chain.run(q)
        result = chain({"question": q}, return_only_outputs=True)
        self.last_sources = retriever.last_sources
        return result['answer']

    def format_data_sources(self):
        return [s['source'] + ': ' + s['final_content'] for s in self.last_sources] if self.last_sources else []

    def reconstruct_memory(self, history):
        # Reconstruct short/long term memory
        llm = AzureOpenAI(deployment_name=self.gpt_deployment, temperature=0, openai_api_key=openai.api_key)
        memory = ConversationSummaryBufferMemory(
            memory_key="chat_history",  # important to align with agent prompt (below)
            max_token_limit=500,
            llm=llm
        )
        for message in history[-20: -1]:  # Forget messages older than 20 interactions
            if 'user' in message:
                memory.buffer.append(HumanMessage(content=message['user']))
            if 'bot' in message:
                memory.buffer.append(AIMessage(content=message['bot']))
        memory.prune()  # Condense older messages to summary
        return memory
        
    def run(self, history: list[dict], overrides: dict) -> any:

        # Get lastest question
        q = history[-1]['user']

        # Use to capture thought process during iterations
        cb_handler = HtmlCallbackHandler()
        cb_manager = CallbackManager(handlers=[cb_handler])

        tools = [
            Tool(name="BMOSearch",
                 func=lambda q: self.bmo_search(q, overrides),
                 description="useful for answering questions about the employee, their insurances, benefits and other personal information",
                 callbacks=cb_manager,
                 return_direct=True)

            # Tool(name="OtherQuestions",
            #     func=lambda q:q,
            #     description="MUST use this tool when the question asks for information on other banks, organizaions, " \
            #                 "or individual such as HSBC, TD, RBC, or if user asks math questions such as \"what is 1+1\"",
            #     return_direct=True
            # )
        ]

        memory = self.reconstruct_memory(history)

        llm_chat = AzureOpenAI(deployment_name=self.chatgpt_deployment, temperature=overrides.get("temperature") or 0.3, openai_api_key=openai.api_key)

        # Main chain
        prompt = ConversationalAgent.create_prompt(
            tools=tools,
            prefix=overrides.get("prompt_template_prefix") or main_prompt_template_prefix,
            suffix=overrides.get("prompt_template_prefix") or main_prompt_template_suffix,  # Must align memory_key (above)
            input_variables = ["input", "agent_scratchpad", "chat_history"]
        )

        chain = LLMChain(llm=llm_chat, prompt=prompt)
        executor = StatelessAgentExecutor.from_agent_and_tools(
            agent=ConversationalAgent(llm_chain=chain, tools=tools, output_parser=EarlyStopConvoOutputParser()),
            tools=tools,
            verbose=True,
            memory=memory,
            early_stopping_method="generate",
            return_only_outputs=True,
            callback_manager=cb_manager
        )
        result = executor.run(q)

        # Remove references to tool names that might be confused with a citation
        result = result.replace("[BMOSearch]", "")  # .replace("[OtherQuestions]", "")

        return {"data_points": self.format_data_sources(), "answer": result, "thoughts": cb_handler.get_and_reset_log()}

