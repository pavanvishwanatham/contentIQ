import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

# Azure AI Search configuration
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "doc-index")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_SERVICE = os.getenv("OPENAI_SERVICE")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")

# Create a SearchClient instance
search_client = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    index_name=AZURE_SEARCH_INDEX,
    credential=AzureKeyCredential(AZURE_SEARCH_KEY)
)

def search_documents(query, top_k=5):
    try:
        results = search_client.search(query, top=top_k)
        return [doc for doc in results]
    except Exception as e:
        print(f"Error during search: {str(e)}")
        return [] 
    