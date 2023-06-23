import openai

from tenacity import retry, wait_random_exponential, stop_after_attempt
from azure.search.documents.models import Vector, QueryType
from azure.search.documents import SearchClient, SearchItemPaged
from enum import Enum
from text import nonewlines

from typing import Dict, List, Optional
from pydantic import BaseModel, Extra
from langchain.schema import BaseRetriever, Document, Field


class SearchModes(Enum):   # Mode                  Estimated cost
    Basic = 'basic'        # Keyword based ranking $
    Vector = 'vector'      # Vector only ANN       $
    Semantic = 'semantic'  # Azure ML ranking      $$$
    Hybrid = 'hybrid'      # basic + vector        $$
    SemanticHybrid = 'semantic_hybrid'  # semantic + vector $$$$


class Retriever(BaseRetriever, BaseModel):  # Extending these two classes causes it to be recognized by langchain
    search_client: SearchClient
    embedding_deployment: str
    search_kwargs: Optional[dict] = Field(default_factory=dict)
    last_sources: Optional[list[dict]]

    class Config:
        extra = Extra.forbid
        arbitrary_types_allowed = True

    def get_relevant_documents(self, query: str) -> List[Document]:
        results = self.retrieve(query, **self.search_kwargs)

        documents = [Document(
            page_content=r['final_content'],
            metadata=r
        ) for r in results]

        return documents

    def aget_relevant_documents(self, query: str) -> List[Document]:
        return self.get_relevant_documents(query)

    def retrieve(self, query, mode=SearchModes.Vector, top=3, filter=None, vector_search_k=3, use_semantic_captions=False, contents_max_len=1500):
        documents = None
        select = ["title", "content", "category", "source"]
        if mode == SearchModes.Basic:
            documents = self.search_client.search(search_text=query, filter=filter, top=top, select=select)
        elif mode == SearchModes.Vector:
            documents = self.search_client.search(
                search_text="",
                filter=filter,
                vector=Vector(value=self.generate_embeddings(query), k=vector_search_k, fields="contentVector"),
                top=top,
                select=select
            )
        elif mode == SearchModes.Semantic:
            documents = self.search_client.search(
                search_text="",
                filter=filter,
                query_type=QueryType.SEMANTIC,
                query_language="en-us",
                query_speller="lexicon",
                semantic_configuration_name="default",
                query_caption="extractive|highlight-false" if use_semantic_captions else None,
                top=top,
                select=select
            )
        elif mode == SearchModes.Hybrid:
            documents = self.search_client.search(
                search_text=query,
                filter=filter,
                vector=Vector(value=self.generate_embeddings(query), k=vector_search_k, fields="contentVector"),
                top=top,
                select=select
            )
        elif mode == SearchModes.SemanticHybrid:
            documents = self.search_client.search(
                search_text="",
                filter=filter,
                vector=Vector(value=self.generate_embeddings(query), k=vector_search_k, fields="contentVector"),
                query_type=QueryType.SEMANTIC,
                query_language="en-us",
                query_speller="lexicon",
                semantic_configuration_name="default",
                query_caption="extractive|highlight-false" if use_semantic_captions else None,
                top=top,
                select=select
            )

        formatted_documents = []
        for doc in documents:
            if use_semantic_captions:
                final_content = nonewlines(". ".join([c.text for c in doc['@search.captions']]))
            else:
                final_content = nonewlines(doc['content'][:contents_max_len])
            formatted_documents.append({
                **doc,
                'content': doc['content'].replace('B M O', 'BMO'),
                'final_content': final_content.replace('B M O', 'BMO')
            })

        self.last_sources = formatted_documents
        return formatted_documents


    # Function to generate embeddings for title and content fields, also used for query embeddings
    @retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def generate_embeddings(self, text):
        response = openai.Embedding.create(input=text, engine=self.embedding_deployment)
        embeddings = response['data'][0]['embedding']
        return embeddings
