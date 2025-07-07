import os
import json
import numpy as np
from openai import AzureOpenAI
from dotenv import load_dotenv
from typing import List, Dict, Tuple
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta

class DocumentRetriever:
    def __init__(self, max_context_length: int = 5000):
        # Load environment variables
        load_dotenv()
        
        # Initialize Azure OpenAI client
        self.openai_client = AzureOpenAI(
            api_key=os.getenv('AZURE_API_KEY'),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv('AZURE_ENDPOINT')
        )
        
        self.embedding_model = "text-embedding-ada-002"
        self.vectors_dir = "vectors"
        self.max_context_length = max_context_length
        
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a query text."""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {str(e)}")
            return None

    def load_vectors(self, container_name: str) -> Tuple[np.ndarray, List[Dict]]:
        """Load vectors and metadata for a container."""
        try:
            # Find the most recent vector files for the container
            vector_files = [f for f in os.listdir(self.vectors_dir) 
                          if f.startswith(f"{container_name}_embeddings_") and f.endswith('.npy')]
            
            if not vector_files:
                return None, None
                
            # Get the most recent file
            latest_vector_file = sorted(vector_files)[-1]
            latest_metadata_file = latest_vector_file.replace('embeddings_', 'metadata_').replace('.npy', '.json')
            
            # Load vectors and metadata
            vectors = np.load(os.path.join(self.vectors_dir, latest_vector_file))
            with open(os.path.join(self.vectors_dir, latest_metadata_file), 'r') as f:
                metadata = json.load(f)
                
            return vectors, metadata
        except Exception as e:
            print(f"Error loading vectors: {str(e)}")
            return None, None

    def semantic_search(self, query: str, container_name: str, top_k: int = 3) -> List[Dict]:
        """Perform semantic search on documents."""
        # Get query embedding
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            return []
            
        # Load vectors and metadata
        vectors, metadata = self.load_vectors(container_name)
        if vectors is None or metadata is None:
            return []
            
        # Calculate cosine similarity
        query_embedding = np.array(query_embedding)
        similarities = np.dot(vectors, query_embedding) / (
            np.linalg.norm(vectors, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top k results
        top_indices = np.argsort(similarities)[-top_k*3:][::-1]  # Get more results initially to allow for deduplication
        
        # Deduplicate results by (container, blob_name), keeping the most relevant chunk
        seen_docs = set()
        results = []
        for idx in top_indices:
            doc_key = (metadata[idx]['container'], metadata[idx]['blob_name'])
            if doc_key not in seen_docs:
                seen_docs.add(doc_key)
                # Truncate content if it exceeds max_context_length
                content = metadata[idx]['content']
                if len(content) > self.max_context_length:
                    content = content[:self.max_context_length] + "..."
                
                results.append({
                    'document': {**metadata[idx], 'content': content},
                    'similarity': float(similarities[idx])
                })
                
                if len(results) >= top_k:  # Stop once we have enough unique documents
                    break
        return results

    def answer_question(self, question: str, context: str) -> str:
        """Generate an answer based on the question and context."""
        try:
            # Truncate context if it exceeds max_context_length
            if len(context) > self.max_context_length:
                context = context[:self.max_context_length] + "..."
                
            response = self.openai_client.chat.completions.create(
                model=os.getenv('DEPLOYMENT_NAME'),
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context. If the answer cannot be found in the context, say so."},
                    {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating answer: {str(e)}")
            return "Sorry, I couldn't generate an answer at this time."

    def generate_blob_sas_url(self, container_name: str, blob_name: str, expiry_minutes: int = 15) -> str:
        """Generate a SAS URL for a blob to allow secure access."""
        try:
            load_dotenv()
            connection_string = os.getenv('AZURE_CONNECTION_STRING')
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            sas_token = generate_blob_sas(
                account_name=blob_service_client.account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=blob_service_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
            )
            blob_url = blob_service_client.get_blob_client(container=container_name, blob=blob_name).url
            return f"{blob_url}?{sas_token}"
        except Exception as e:
            print(f"Error generating SAS URL: {str(e)}")
            return None