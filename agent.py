import requests
import os
from langgraph.graph import StateGraph, END
from openai import AzureOpenAI
from typing import TypedDict, Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

print("AZURE_OPENAI_API_KEY:", os.getenv("AZURE_OPENAI_API_KEY"))
print("AZURE_ENDPOINT:", os.getenv("AZURE_ENDPOINT"))

# Set environment variables or hardcode here
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_ENDPOINT")

# Azure OpenAI client setup
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-01-1",
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

# Define the StateGraph schema
class AgentState(TypedDict, total=False):
    user_input: str
    next: str  # Used by the router to indicate the next node
    response: str # The final response to the user
    topic: Optional[str] # The extracted topic for document search
    docs: Optional[List[Dict[str, Any]]] # The search results (list of dictionaries)

# Import nodes from nodes.py
from nodes import router_node, chat_node, extract_topic_node, search_index_node, format_results_node, final_output_node

# Helper to chat with Azure OpenAI
def openai_chat(deployment, prompt):
    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return response.choices[0].message.content.strip()

# Build LangGraph
workflow = StateGraph(AgentState)
workflow.add_node("router", router_node)
workflow.add_node("chat_node", chat_node)
workflow.add_node("extract_topic", extract_topic_node)
workflow.add_node("search_index", search_index_node)
workflow.add_node("format_results", format_results_node)
workflow.add_node("final_output_node", final_output_node)

workflow.set_entry_point("router")

workflow.add_conditional_edges(
    "router",  # Source node
    lambda x: x["next"],  # Function to get the condition from the state
    {
        "chat_node": "chat_node",  # If 'next' is "chat_node", go to "chat_node"
        "extract_topic": "extract_topic",  # If 'next' is "extract_topic", go to "extract_topic"
    }
)

workflow.add_edge("extract_topic", "search_index")
workflow.add_edge("search_index", "format_results")

# Define exit points by adding edges to final_output_node, which then goes to END
workflow.add_edge("chat_node", "final_output_node")
workflow.add_edge("format_results", "final_output_node")
workflow.add_edge("final_output_node", END)

agent = workflow.compile()

if __name__ == "__main__":
    while True:
        user_input = input("\nYou: ")
        result = agent.invoke({"user_input": user_input})
        print("\nAgent:", result["response"])
