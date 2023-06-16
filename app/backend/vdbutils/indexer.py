# Import required libraries  
import os  
import re
import openai
import time
# from dotenv import load_dotenv
from tenacity import retry, wait_random_exponential, stop_after_attempt 
# from azure.core.credentials import AzureKeyCredential  
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient  
from azure.search.documents.indexes import SearchIndexClient  
# from azure.search.documents.models import Vector
from azure.search.documents.indexes.models import (  
    SearchIndex,  
    SearchField,  
    SearchFieldDataType,  
    SimpleField,  
    SearchableField,  
    SearchIndex,  
    SemanticConfiguration,  
    PrioritizedFields,  
    SemanticField,  
    SearchField,  
    SemanticSettings,  
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    HnswParameters
)  
VERBOSE = os.environ.get('VERBOSE') or True
AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE") or "gptkb"
  
# load_dotenv()

MAX_SECTION_LENGTH = 950
SENTENCE_SEARCH_LIMIT = 100
SECTION_OVERLAP = 100


class Indexer(object):
    def __init__(self, index_client: SearchIndexClient, index_name: str, embedding_deployment: str):
        """
        In this class "document" will be mentioned a lot. Document means JSON Document in this context. 
        Document expected format:
        {
            title: ***,
            content: ***,
            source: ***.html,
            category: ***
        }
        """
        self.index_client = index_client
        self.index_name = index_name
        self.embedding_deployment = embedding_deployment

        self.ensure_search_index()
        self.search_client = SearchClient(
            endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
            index_name=self.index_name,
            credential=DefaultAzureCredential())


    ###################
    #  Main handlers
    ###################
    def index(self, document):
        sections = self.create_sections(document)
        self.index_sections(document, sections)

    def remove_from_index(self, document={}):
        source = document.get('source')
        if VERBOSE: print(f"Removing sections from '{source or '<all>'}' from search index '{self.index_name}'")

        while True:
            filter = None if source == None else f"source eq '{source}'"
            r = self.search_client.search("", filter=filter, top=1000, include_total_count=True)
            if r.get_count() == 0:
                break
            r = self.search_client.delete_documents(documents=[{ "id": d["id"] } for d in r])
            if VERBOSE: print(f"\tRemoved {len(r)} sections from index")
            # It can take a few seconds for search results to reflect changes, so wait a bit
            time.sleep(2)

    def purge_index(self):
        return self.remove_from_index()
    

    ###################
    #  Helpers
    ###################
    def ensure_search_index(self, force_update=False):
        if force_update or self.index_name not in self.index_client.list_index_names():
            index = SearchIndex(
                name=self.index_name,
                fields = [
                    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                    SearchableField(name="title", type=SearchFieldDataType.String,
                        searchable=True, retrievable=True),
                    SearchableField(name="content", type=SearchFieldDataType.String,
                        searchable=True, retrievable=True),
                    SearchField(name="titleVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        searchable=True, dimensions=1536, vector_search_configuration="default-vector-config"),
                    SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        searchable=True, dimensions=1536, vector_search_configuration="default-vector-config"),
                    SearchableField(name="category", type=SearchFieldDataType.String,
                        filterable=True, searchable=True, retrievable=True),
                    SearchableField(name="source", type=SearchFieldDataType.String,
                        filterable=True, searchable=True, retrievable=True),
                ],
                
                vector_search = VectorSearch(
                    algorithm_configurations=[
                        VectorSearchAlgorithmConfiguration(
                            name="default-vector-config",
                            kind="hnsw",
                            hnsw_parameters=HnswParameters(
                                m=4,
                                ef_construction=400,
                                ef_search=1000,
                                metric="cosine"
                            )
                        )
                    ]
                ),
                semantic_settings=SemanticSettings(
                    configurations=[
                        SemanticConfiguration(
                            name='default',
                            prioritized_fields=PrioritizedFields(
                                title_field=SemanticField(field_name="title"),
                                prioritized_keywords_fields=[SemanticField(field_name="category")],
                                prioritized_content_fields=[SemanticField(field_name="content")]
                            )
                        )
                    ]
                )
            )
            if VERBOSE: print(f"Creating or updating {self.index_name} search index")
            self.index_client.create_or_update_index(index)
        else:
            if VERBOSE: print(f"Search index {self.index_name} already exists")

    @classmethod
    def split_text(cls, document):
        SENTENCE_ENDINGS = [".", "!", "?"]
        WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]
        if VERBOSE: print(f"Splitting '{document['source']}' into sections")

        all_text = cls.cleanup_text(document['content'])
        length = len(all_text)
        start = 0
        end = length
        while start + SECTION_OVERLAP < length:
            last_word = -1
            end = start + MAX_SECTION_LENGTH

            if end > length:
                end = length
            else:
                # Try to find the end of the sentence
                while end < length and (end - start - MAX_SECTION_LENGTH) < SENTENCE_SEARCH_LIMIT and all_text[end] not in SENTENCE_ENDINGS:
                    if all_text[end] in WORDS_BREAKS:
                        last_word = end
                    end += 1
                if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
                    end = last_word # Fall back to at least keeping a whole word
            if end < length:
                end += 1

            # Try to find the start of the sentence or at least a whole word boundary
            last_word = -1
            while start > 0 and start > end - MAX_SECTION_LENGTH - 2 * SENTENCE_SEARCH_LIMIT and all_text[start] not in SENTENCE_ENDINGS:
                if all_text[start] in WORDS_BREAKS:
                    last_word = start
                start -= 1
            if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
                start = last_word
            if start > 0:
                start += 1

            section_text = all_text[start:end]
            yield section_text

            start = end - SECTION_OVERLAP
            
        if start + SECTION_OVERLAP < end:
            yield all_text[start:end]

    @classmethod
    def cleanup_text(cls, text):
        return re.sub(r'[\s\n]+\n', '\n', text.strip())

    @classmethod
    def get_id(cls, document):
        return re.sub("[^0-9a-zA-Z_-]","_",f"{document['source']}")

    def create_sections(self, document):
        for i, section in enumerate(self.split_text(document)):
            yield {
                "id": self.get_id(document) + f"-{i}",
                "title": document['title'],
                "content": section,
                "titleVector": self.generate_embeddings(document['title']),
                "contentVector": self.generate_embeddings(section),
                "category": document['category'],
                "source": document['source'],
                "@search.action": "upload"
            }

        
    # Function to generate embeddings for title and content fields, also used for query embeddings
    @retry(wait=wait_random_exponential(min=1, max=15), stop=stop_after_attempt(4))
    def generate_embeddings(self, text):
        response = openai.Embedding.create(input=text, engine=self.embedding_deployment)
        embeddings = response['data'][0]['embedding']
        return embeddings


    def index_sections(self, document, sections):
        if VERBOSE: print(f"Indexing sections from '{document['source']}' into search index '{self.index_name}'")

        # Using this apparently stupid method cuz sections is generator and we want to save RAM
        i = 0
        batch = []
        for s in sections:
            batch.append(s)
            i += 1
            if i % 1000 == 0:
                results = self.search_client.upload_documents(documents=batch)
                succeeded = sum([1 for r in results if r.succeeded])
                if VERBOSE: print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")
                batch = []

        if len(batch) > 0:
            results = self.search_client.upload_documents(documents=batch)
            succeeded = sum([1 for r in results if r.succeeded])
            if VERBOSE: print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")
    
