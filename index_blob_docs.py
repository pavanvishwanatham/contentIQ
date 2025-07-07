# index_blob_docs.py

import os
import tempfile
import openai
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType,
    SimpleField, SearchableField, VectorSearch,
    VectorSearchAlgorithmKind, HnswParameters,
    HnswAlgorithmConfiguration, VectorSearchProfile
)
from azure.storage.blob import ContainerClient
from langchain_community.document_loaders import PyPDFLoader, UnstructuredPowerPointLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
import re

# Load .env
load_dotenv()

# Load ENV variables
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_STORAGE_CONN = os.getenv("AZURE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "doc-index")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_API_KEY")
# Set OpenAI config
openai.api_type = "azure"
openai.api_base = AZURE_OPENAI_ENDPOINT
openai.api_version = "2023-05-15"
openai.api_key = AZURE_OPENAI_KEY

embedding_model = AzureOpenAIEmbeddings(
    deployment="text-embedding-ada-002",
    openai_api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    openai_api_type="azure",
    openai_api_version="2023-05-15"
)

def create_index():
    index_client = SearchIndexClient(AZURE_SEARCH_ENDPOINT, AzureKeyCredential(AZURE_SEARCH_KEY))

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=1536,
            vector_search_profile_name="my-vector-profile"
        )
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="my-hnsw",
                kind=VectorSearchAlgorithmKind.HNSW,
                parameters=HnswParameters(metric="cosine", m=4)  # efConstruction removed due to Azure SDK warning
            )
        ],
        profiles=[
            VectorSearchProfile(name="my-vector-profile", algorithm_configuration_name="my-hnsw")
        ]
    )

    index = SearchIndex(
        name=AZURE_SEARCH_INDEX,
        fields=fields,
        vector_search=vector_search
    )

    print(f"🔧 Creating index: {AZURE_SEARCH_INDEX}")
    index_client.create_or_update_index(index)
    print("✅ Index created.")

def index_documents():
    blob_client = ContainerClient.from_connection_string(AZURE_STORAGE_CONN, AZURE_STORAGE_CONTAINER)
    search_client = SearchClient(AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_INDEX, AzureKeyCredential(AZURE_SEARCH_KEY))

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    for blob in blob_client.list_blobs():
        if not (blob.name.lower().endswith(".pdf") or blob.name.lower().endswith(".pptx")):
            continue

        print(f"\n📄 Processing: {blob.name}")
        blob_data = blob_client.get_blob_client(blob).download_blob().readall()

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(blob.name)[-1]) as tmp_file:
            tmp_file.write(blob_data)
            path = tmp_file.name

        if path.lower().endswith(".pdf"):
            loader = PyPDFLoader(path)
        else:
            loader = UnstructuredPowerPointLoader(path)
        docs = loader.load_and_split(text_splitter)

        for i, chunk in enumerate(docs):
            safe_blob_name = re.sub(r'[^A-Za-z0-9_\-=]', '_', blob.name)
            vector = embedding_model.embed_query(chunk.page_content)
            doc = {
                "id": f"{safe_blob_name}-{i}",
                "title": blob.name,
                "content": chunk.page_content,
                "content_vector": vector
            }
            search_client.upload_documents(documents=[doc])

        os.remove(path)
        print(f"✅ Indexed: {blob.name}")

if __name__ == "__main__":
    create_index()
    index_documents()
    print(f"\n📦 All documents embedded and indexed into '{AZURE_SEARCH_INDEX}'")
