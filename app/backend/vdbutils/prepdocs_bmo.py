# ! pip install --extra-index-url https://pkgs.dev.azure.com/azure-sdk/public/_packaging/azure-sdk-for-python/pypi/simple/ azure-search-documents==11.4.0a20230509004

import os
import openai
from azure.identity import DefaultAzureCredential

import glob
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient


AZURE_SEARCH_SERVICE = "gptkb-nnljxrgpw3pfk"
AZURE_SEARCH_INDEX = "gptkbindex"
AZURE_OPENAI_SERVICE = "cog-nnljxrgpw3pfk"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = "ada"

os.environ['AZURE_SEARCH_SERVICE'] = AZURE_SEARCH_SERVICE
os.environ['VERBOSE'] = "true"

from app.backend.vdbutils.indexer import Indexer

# Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and Blob Storage (no secrets needed, 
# just use 'az login' locally, and managed identity when deployed on Azure). If you need to use keys, use separate AzureKeyCredential instances with the 
# keys for each service
# If you encounter a blocking error during a DefaultAzureCredntial resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True)
azure_credential = DefaultAzureCredential()

# Used by the OpenAI SDK
openai.api_type = "azure"
openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
openai.api_version = "2022-12-01"

# Comment these two lines out if using keys, set your API key in the OPENAI_API_KEY environment variable instead
openai.api_type = "azure_ad"
openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
openai.api_key = openai_token.token

# Set up clients for Cognitive Search and Storage
search_client = SearchClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
    index_name=AZURE_SEARCH_INDEX,
    credential=azure_credential)

index_client = SearchIndexClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net/",
    credential=azure_credential)

# crawler = Crawler(...)
indexer = Indexer(index_client, AZURE_SEARCH_INDEX, AZURE_OPENAI_EMBEDDING_DEPLOYMENT)
indexer.purge_index()

for file in glob.glob('../../../data/BMOcomCloned/**/*.txt', recursive=True):
    if file.endswith('meta.txt'):
        continue
    meta_file = file.replace('.txt', '.meta.txt')
    title = os.path.basename(file).rsplit('.')[0]
    source = ''
    category = 'domain'
    with open(file, encoding='utf8') as f:
        content = f.read()
    with open(meta_file, encoding='utf8') as f:
        lines = f.readlines()
        if len(lines) >= 2:
            source, title = lines[:2]
        elif len(lines) == 1:
            source = lines[0]
    document = {
        'title': title.strip(),
        'content': content.strip(),
        'source': source.strip(),
        'category': category
    }
    indexer.index(document)
