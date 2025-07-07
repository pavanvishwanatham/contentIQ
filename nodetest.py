# nodes.py

import warnings
warnings.filterwarnings("ignore")

from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import StrOutputParser
import re, requests, os, json
from nodes import generate_blob_sas_url  # imported for SAS URL generation
import os


llm = AzureChatOpenAI(
    deployment_name="gpt-4o",
    temperature=0,
    api_version="2023-05-15",
    azure_endpoint=os.getenv("AZURE_ENDPOINT")
)
parser = StrOutputParser()

AZURE_BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "contentiq")


def router_node(input):
    query = input["user_input"].lower()
    print(f"Router Node received: {query}")

    intent_prompt = (
    "You are a routing classifier that decides whether a user input is meant for chatting with the assistant "
    "(e.g., asking questions, seeking definitions, conversational replies) OR searching for documents "
    "(e.g., requesting files, papers, PDFs, or documents).\n\n"
    "Return only one word: 'chat' or 'doc_search'.\n\n"
    "Examples:\n"
    "- 'What is Power Automate?' -> chat\n"
    "- 'Tell me how Power BI works' -> chat\n"
    "- 'Search for documents on Power BI' -> doc_search\n"
    "- 'Find docs about Microsoft Fabric' -> doc_search\n"
    "- 'Give me whitepapers on machine learning' -> doc_search\n"
    "- 'What’s the use of Power Apps?' -> chat\n\n"
    f"User input: {input['user_input']}"
    )
    
    try:
        intent = llm.invoke(intent_prompt).content.strip().lower()
    except Exception as e:
        print(f"Error classifying intent with LLM: {e}. Defaulting to chat.")
        intent = "chat"

    print(f"LLM classified intent as: {intent}")
    return {
        "next": "extract_topic" if intent == "doc_search" else "chat_node",
        "user_input": input["user_input"],
        "chat_history": input.get("chat_history", [])
    }

def chat_node(input):
    print(f"Chat Node received: {input['user_input']}")
    user_input = input["user_input"]
    chat_history = input.get("chat_history", [])

    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for turn in chat_history:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    messages.append({"role": "user", "content": user_input})

    response = llm.invoke(messages)
    assistant_reply = response.content

    chat_history.append({"user": user_input, "assistant": assistant_reply})
    return {"response": assistant_reply, "chat_history": chat_history}

def extract_topic_node(input):
    print(f"Extract Topic Node received: {input['user_input']}")
    user_input = input["user_input"]
    chat_history = input.get("chat_history", [])

    # Collect recent context to help resolve pronouns like "it"
    recent_context = ""
    for turn in chat_history[-3:]:  # Use last 3 exchanges for context
        recent_context += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n"

    # Prompt for LLM to extract topic with context
    prompt = (
        "You are an assistant that extracts the most relevant topic from a user message, "
        "using the recent conversation for reference if the topic is vague.\n\n"
        f"Recent Conversation:\n{recent_context}\n"
        f"Current User Input: {user_input}\n\n"
        "Return the exact topic being referred to in one short phrase."
    )

    try:
        topic = llm.invoke(prompt).content.strip()
    except Exception as e:
        print(f"Error in topic extraction: {e}")
        topic = "unknown"

    print(f"Extracted topic: {topic}")
    return {
        "topic": topic,
        "chat_history": chat_history,
        "user_input": user_input
    }

def search_index_node(input):
    print(f"Search Index Node received topic: {input['topic']}")
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
    INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX")

    headers = {"Content-Type": "application/json", "api-key": AZURE_SEARCH_KEY}
    search_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{INDEX_NAME}/docs/search?api-version=2023-07-01-preview"
    data = {"search": input["topic"], "top": 1000
            }

    try:
        res = requests.post(search_url, headers=headers, json=data)
        res.raise_for_status()
        hits = res.json().get("value", [])
    except requests.exceptions.RequestException as e:
        print(f"Error during Azure AI Search: {e}")
        hits = []

    return {
        "docs": hits,
        "chat_history": input.get("chat_history", []),
        "user_input": input["user_input"]
    }

def format_results_node(input):
    results = input["docs"]
    if not results:
        return {"response": "❌ No matching documents found.", "chat_history": input.get("chat_history", [])}

    grouped = {}
    for doc in results:
        # Prefer grouping by source if available, otherwise fallback to URL
        key = doc.get("source") or doc.get("url") or doc.get("title")
        if key and key not in grouped:
            grouped[key] = doc  # Only store the first hit from each document

    unique_results = list(grouped.values())

    response = f"\n📚 *Top Matching Documents*\n{'='*35}\nFound {len(unique_results)} unique result(s):\n"
    for i, doc in enumerate(unique_results[:5], 1):
        title  = doc.get("title", "Untitled")
        doc_id = doc.get("id", "N/A")
        source = doc.get("source")

        # Generate a time-limited SAS link for the blob
        blob_name = title  # adjust if blob naming differs
        sas_url    = generate_blob_sas_url(AZURE_BLOB_CONTAINER, blob_name)

        response += f"\n🔹 *{i}. {title}*\n"
        response += f"   - 🆔 ID: ⁠ {doc_id} ⁠\n"
        if source:
            response += f"   - 📁 Source: ⁠ {source} ⁠\n"
        response += f"   - 🔗 [View Document]({sas_url})\n"

    response += "\n" + "="*35
    return {"response": response.strip(), "chat_history": input.get("chat_history", [])}

def final_output_node(input):
    return {"response": input["response"], "chat_history": input.get("chat_history", [])}
