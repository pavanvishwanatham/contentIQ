# agent.py

import requests
import os
from langgraph.graph import StateGraph, END
from openai import AzureOpenAI
from typing import TypedDict, Optional, List, Dict, Any


# Set environment variables or hardcode here
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_ENDPOINT")

# Azure OpenAI client setup
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-05-15",
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

# Define the StateGraph schema
class AgentState(TypedDict, total=False):
    user_input: str
    next: str
    response: str
    topic: Optional[str]
    docs: Optional[List[Dict[str, Any]]]
    chat_history: List[Dict[str, str]]  # Added chat memory

# Import nodes
from nodetest import (
    router_node, chat_node, extract_topic_node,
    search_index_node, format_results_node, final_output_node
)

# Build LangGraph
workflow = StateGraph(AgentState)
workflow.add_node("router", router_node)
workflow.add_node("chat_node", chat_node)
workflow.add_node("extract_topic", extract_topic_node)
workflow.add_node("search_index", search_index_node)
workflow.add_node("format_results", format_results_node)
workflow.add_node("final_output_node", final_output_node)

workflow.set_entry_point("router")

workflow.add_conditional_edges("router", lambda x: x["next"], {
    "chat_node": "chat_node",
    "extract_topic": "extract_topic",
})

workflow.add_edge("extract_topic", "search_index")
workflow.add_edge("search_index", "format_results")
workflow.add_edge("chat_node", "final_output_node")
workflow.add_edge("format_results", "final_output_node")
workflow.add_edge("final_output_node", END)

agent = workflow.compile()

if __name__ == "__main__":
    print("Hello! How can I help you today?")
    chat_history = []
    while True:
        user_input = input("\nYou: ")
        result = agent.invoke({
            "user_input": user_input,
            "chat_history": chat_history
        })
        print("\nAgent:", result["response"])
        chat_history = result.get("chat_history", [])