# nodes.py

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from langchain.chat_models import AzureChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate
import re
import requests
import os
import json
import html
from typing import Dict, Any, List
import textwrap 
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

llm = AzureChatOpenAI(
    deployment_name="gpt-4o",
    temperature=0,
    api_version="2023-05-15",
    azure_endpoint=os.getenv("AZURE_ENDPOINT")
)
parser = StrOutputParser()

TOP_K = 5

# Detects if it's a normal chat or doc search
def input_router(state):
    query = state["input"]
    if re.search(r"(find|search|documents|docs|papers|files)", query, re.IGNORECASE):
        return {**state, "__next__": "TopicExtractor"}
    else:
        return {**state, "__next__": "ConversationNode"}

# LangGraph nodes - moved from agent.py
def router_node(input):
    query = input["user_input"].lower()
    print(f"Router Node received: {query}") # Debugging print
    
    # Use LLM to classify intent
    intent_prompt = (
        "You are an AI assistant that classifies user intent. "
        "Based on the following user input, determine if the user wants a general conversation (chat) "
        "or to search for documents (doc_search). "
        "Respond with only 'chat' or 'doc_search'.\n\n" # Ensure single word output
        f"User input: {input['user_input']}"
    )
    
    # Use llm.invoke directly if it's already configured to return content
    # Otherwise, use openai_chat helper if it's preferred for direct chat completion
    # Assuming llm.invoke is suitable here and returns a content attribute
    try:
        intent = llm.invoke(intent_prompt).content.strip().lower()
    except Exception as e:
        print(f"Error classifying intent with LLM: {e}. Defaulting to chat.")
        intent = "chat" # Fallback in case of LLM error

    print(f"LLM classified intent as: {intent}") # Debugging print

    if intent == "doc_search":
        print("Router decided: extract_topic (based on LLM classification)") # Debugging print
        return {"next": "extract_topic", "user_input": input["user_input"]}
    else:
        print("Router decided: chat_node (based on LLM classification or fallback)") # Debugging print
        return {"next": "chat_node", "user_input": input["user_input"]}

def chat_node(input):
    print(f"Chat Node received: {input['user_input']}") # Debugging print
    response = llm.invoke(input["user_input"])
    print(f"Chat Node response: {response.content}") # Debugging print
    return {"response": response.content}

def extract_topic_node(input):
    print(f"Extract Topic Node received: {input['user_input']}") # Debugging print
    prompt = f"Extract the topic from this user request: '{input['user_input']}'. Just return the topic."
    topic = llm.invoke(prompt).content.strip()
    print(f"Extracted topic: {topic}") # Debugging print
    return {"topic": topic}

def search_index_node(input):
    print(f"Search Index Node received topic: {input['topic']}") # Debugging print
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
    INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX")
    print(f"Search Endpoint: {AZURE_SEARCH_ENDPOINT}") # Debugging print
    print(f"Search Key (first 5 chars): {AZURE_SEARCH_KEY[:5] if AZURE_SEARCH_KEY else 'N/A'}") # Debugging print
    print(f"Search Index: {INDEX_NAME}") # Debugging print

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_SEARCH_KEY
    }
    search_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{INDEX_NAME}/docs/search?api-version=2023-07-01-preview"
    data = {
        "search": input['topic'],
        "top": 1000  # Azure maximum per page
        # Removed semantic search parameters - assuming this was applied
    }
    print(f"Search request data payload: {json.dumps(data)}") # Debugging print: print the JSON payload

    try:
        res = requests.post(search_url, headers=headers, json=data)
        res.raise_for_status() # Raise an exception for HTTP errors
        hits = res.json().get("value", [])
        print(f"Search results count: {len(hits)}") # Debugging print
    except requests.exceptions.RequestException as e:
        print(f"Error during Azure AI Search: {e}")
        if 'res' in locals() and res is not None: # Check if response object exists before trying to access .text
            print(f"Azure AI Search response content: {res.text}") # Debugging print: full response content
        hits = [] # Ensure hits is defined even on error
        
    return {"docs": hits}

def generate_blob_sas_url(container_name, blob_name, expiry_minutes=10):
    AZURE_CONNECTION_STRING = os.getenv("AZURE_CONNECTION_STRING")
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
    )
    blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{urllib.parse.quote(blob_name)}?{sas_token}"
    return blob_url

def format_results_node(input: Dict[str, Any]) -> Dict[str, Any]:
    docs: List[Dict[str, Any]] = input.get("docs", []) or []
    container = input.get("container")   # use propagated container

    # Map best chunk per document
    best_by_doc: Dict[str, Dict[str, Any]] = {}
    for doc in docs:
        blob_key = doc.get('metadata_storage_name') or doc.get('title') or doc.get('id', '')
        score = doc.get('@search.score', 0)
        if blob_key not in best_by_doc or score > best_by_doc[blob_key].get('@search.score', 0):
            best_by_doc[blob_key] = doc
    # Sort unique docs by descending score and take top 5
    unique_docs = sorted(
        best_by_doc.values(),
        key=lambda d: d.get('@search.score', 0),
        reverse=True
    )[:TOP_K]

    AZURE_BLOB_CONTAINER = "contentiq"
    header = "Here are the top documents I found (most relevant first):"
    html_lines = ["<style>.search-results a { text-decoration: none !important; }</style>", "<div class='search-results'>"]
    for idx, d in enumerate(unique_docs, start=1):
        blob_name = d.get('title', '')  # title is the blob name
        title = blob_name
        score = d.get('@search.score', 0)
        snippet = (d.get('content', '')[:200] + '...') if d.get('content') else ''

        sas_url = generate_blob_sas_url(AZURE_BLOB_CONTAINER, blob_name)
        # Inject JavaScript function for download if not already present
        # (This will be included once at the top of the results)
        if idx == 1:
            html_lines.append('''<script>
function downloadFile(blobName, title) {
    const url = `/download?file=${encodeURIComponent(blobName)}&title=${encodeURIComponent(title)}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = title;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}
</script>''')

        view_link = f"<a href='{sas_url}' target='_blank' rel='noopener noreferrer' style='text-decoration: none;'>   ↗</a>"
        link_html = f"{view_link}"

        html_lines.append(
            f"<div class='search-result-item'>"
            f"<strong>{idx}. {title}</strong>{link_html}"
            f"</div>"
        )
    html_lines.append("</div>")
    html = textwrap.dedent("".join(html_lines))
    return {"response": f"{header}{html}"}

def final_output_node(input):
    print(f"Final Output Node received response: {input['response'][:100]}...") # Debugging print
    # This node simply passes the response along. Add any final logging/processing here.
    return {"response": input["response"]}
