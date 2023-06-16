import openai

from tenacity import retry, wait_random_exponential, stop_after_attempt
from azure.search.documents.models import Vector, QueryType
from azure.search.documents import SearchClient
from enum import Enum


class SearchModes(Enum):
    Basic = 'basic'        # Keyword based ranking
    Vector = 'vector'      # Vector only ANN
    Semantic = 'semantic'  # Azure ML ranking
    Hybrid = 'hybrid'      # basic + vector
    SemanticHybrid = 'semantic_hybrid'  # semantic + vector


class Retriever(object):
    def __init__(self, search_client: SearchClient, embedding_deployment: str):
        self.search_client = search_client
        self.embedding_deployment = embedding_deployment

    def retrieve(self, query, mode=SearchModes.Vector, top=3, filter=None, vector_search_k=3, use_semantic_captions=False):
        results = None
        select = ["title", "content", "category", "source"]
        if mode == SearchModes.Basic:
            results = self.search_client.search(search_text=query, filter=filter, top=top, select=select)
        elif mode == SearchModes.Vector:
            results = self.search_client.search(
                search_text="",
                filter=filter,
                vector=Vector(value=self.generate_embeddings(query), k=vector_search_k, fields="contentVector"),
                top=top,
                select=select
            )
        elif mode == SearchModes.Semantic:
            results = self.search_client.search(
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
            results = self.search_client.search(
                search_text=query,
                filter=filter,
                vector=Vector(value=self.generate_embeddings(query), k=vector_search_k, fields="contentVector"),
                top=top,
                select=select
            )
        elif mode == SearchModes.SemanticHybrid:
            results = self.search_client.search(
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

        return results

    # Function to generate embeddings for title and content fields, also used for query embeddings
    @retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def generate_embeddings(self, text):
        response = openai.Embedding.create(input=text, engine=self.embedding_deployment)
        embeddings = response['data'][0]['embedding']
        return embeddings
