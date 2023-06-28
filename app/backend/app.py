from functools import lru_cache
import json
import os
import mimetypes
import time
import logging
from repr_tool import MyPythonAstREPLTool
import openai
from flask import Flask, request, jsonify
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from approaches.retrievethenread import RetrieveThenReadApproach
from approaches.readretrieveread import ReadRetrieveReadApproach
from approaches.readdecomposeask import ReadDecomposeAsk
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from approaches.chatconversationalreadretrieveread import ChatConversationalReadRetrieveReadApproach
from azure.storage.blob import BlobServiceClient
from langchain.agents import create_pandas_dataframe_agent
from langchain.llms.openai import AzureOpenAI
# from langchain.agents.agent_types import AgentType
import pandas as pd


from vdbutils.indexer import Indexer
from vdbutils.retriever import Retriever

# Replace these with your own values, either in environment variables or directly here
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT") or "mystorageaccount"
AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER") or "content"
AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE") or "gptkb"
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX") or "gptkbindex"
AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE") or "myopenai"
AZURE_OPENAI_GPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT_DEPLOYMENT") or "davinci"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "chat"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT") or "ada"

KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT") or "content"
KB_FIELDS_CATEGORY = os.environ.get("KB_FIELDS_CATEGORY") or "category"
KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE") or "sourcepage"
KB_FIELDS_SOURCE = os.environ.get("KB_FIELDS_SOURCE") or "source"

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

logging.warning(os.environ)

# Set up clients for Cognitive Search and Storage
# index_client = SearchIndexClient(
#     endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net/",
#     credential=azure_credential)
# indexer = Indexer(index_client, AZURE_SEARCH_INDEX, AZURE_OPENAI_EMBEDDING_DEPLOYMENT)

search_client = SearchClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
    index_name=AZURE_SEARCH_INDEX,
    credential=azure_credential)
retriever = Retriever(search_client=search_client, embedding_deployment=AZURE_OPENAI_EMBEDDING_DEPLOYMENT)

blob_client = BlobServiceClient(
    account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net", 
    credential=azure_credential)
blob_container = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)

# Various approaches to integrate GPT and external knowledge, most applications will use a single one of these patterns
# or some derivative, here we include several for exploration purposes
ask_approaches = {
    "rtr": RetrieveThenReadApproach(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "rrr": ReadRetrieveReadApproach(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "rda": ReadDecomposeAsk(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT)
}

chat_approaches = {
    # "rrr": ChatReadRetrieveReadApproach(search_client, AZURE_OPENAI_CHATGPT_DEPLOYMENT, AZURE_OPENAI_GPT_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "rrr": ChatConversationalReadRetrieveReadApproach(search_client, AZURE_OPENAI_CHATGPT_DEPLOYMENT, AZURE_OPENAI_GPT_DEPLOYMENT, AZURE_OPENAI_EMBEDDING_DEPLOYMENT, KB_FIELDS_SOURCE, KB_FIELDS_CONTENT)
}

# crawler = Crawler(...)

app = Flask(__name__)

@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def static_file(path):
    return app.send_static_file(path)

# Serve content files from blob storage from within the app to keep the example self-contained. 
# *** NOTE *** this assumes that the content files are public, or at least that all users of the app
# can access all the files. This is also slow and memory hungry.
@app.route("/content/<path>")
def content_file(path):
    blob = blob_container.get_blob_client(path).download_blob()
    mime_type = blob.properties["content_settings"]["content_type"]
    if mime_type == "application/octet-stream":
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return blob.readall(), 200, {"Content-Type": mime_type, "Content-Disposition": f"inline; filename={path}"}
    
@app.route("/ask", methods=["POST"])
def ask():
    ensure_openai_token()
    approach = request.json["approach"]
    try:
        impl = ask_approaches.get(approach)
        if not impl:
            return jsonify({"error": "unknown approach"}), 400
        r = impl.run(request.json["question"], request.json.get("overrides") or {})
        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /ask")
        return jsonify({"error": str(e)}), 500
    
@app.route("/chat", methods=["POST"])
def chat():
    ensure_openai_token()
    approach = request.json["approach"]
    try:
        impl = chat_approaches.get(approach)
        if not impl:
            return jsonify({"error": "unknown approach"}), 400
        r = impl.run(request.json["history"], request.json.get("overrides") or {})
        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /chat")
        return jsonify({"error": str(e)}), 500

@app.route("/app_review/table/<platform>", methods=["GET"])
def app_review_table(platform):
    if platform not in ["ios", "android"]:
        return jsonify({"error": "unknown platform"}), 400
    return jsonify({
        "table": pd.DataFrame.from_dict(get_app_review_json(platform), orient="columns").to_dict(orient="dict")
    }), 200, {"Content-Type": "application/json"}


@app.route("/app_review/question/<platform>", methods=["POST"])
def app_review_question(platform):
    if platform not in ["ios", "android"]:
        return jsonify({"error": "unknown platform"}), 400
    ensure_openai_token()
    try:
        df = pd.DataFrame.from_dict(get_app_review_json(platform), orient="columns")
        question = request.json["question"]
        PREFIX = """
You are working with a pandas dataframe in Python. The name of the dataframe is `df`.
each row is an app review with its Date, Rating and releated app Version.
The review content is in the Body column.
The topics columns contains a list of summaried issues from the review.
You should use the tools below to answer the question posed of you:"""
        agent = create_pandas_dataframe_agent(
            AzureOpenAI(
                openai_api_key=openai.api_key,
                deployment_name=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
                # openai_api_base=openai.api_base,
                # openai_api_version=openai.api_version,
                temperature=0,
                # model="gpt-3.5-turbo",
            ),
            df,
            verbose=True,
            prefix=PREFIX,
            # agent_type=AgentType.OPENAI_FUNCTIONS,
        )
        tool = MyPythonAstREPLTool(realtool=agent.tools[0])
        agent.tools = [tool]
        answer = agent.run(question)
        # The azure gpt3.5 model wants to ask follow up questions by itself at the end of the answer...
        answer = answer.split('\nQuestion:')[0]
        return jsonify({
            "answer": answer,
            "table": tool.result.to_dict(orient="dict"),
        }), 200, {"Content-Type": "application/json"}
    except Exception as e:
        logging.exception("Exception in /app_review/question")
        return jsonify({"error": str(e)}), 500


@lru_cache()
def get_app_review_json(platform):
    blob = blob_container.get_blob_client(f"app_review/{platform}_negative_result.json").download_blob()
    return json.loads(blob.readall())

def ensure_openai_token():
    global openai_token
    if openai_token.expires_on < int(time.time()) - 60:
        openai_token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
        openai.api_key = openai_token.token
    
if __name__ == "__main__":
    app.run()
