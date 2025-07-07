from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

def list_blob_files():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get connection string from environment variable
    connect_str = os.getenv('AZURE_CONNECTION_STRING')
    
    if not connect_str:
        print("Error: AZURE_CONNECTION_STRING environment variable not set")
        return
    
    try:
        # Create the BlobServiceClient object 
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        
        # List all containers
        containers = blob_service_client.list_containers()
        
        print("Listing all blobs in all containers:")
        print("-" * 50)
        
        # Iterate through all containers
        for container in containers:
            container_client = blob_service_client.get_container_client(container.name)
            print(f"\nContainer: {container.name}")
            print("-" * 30)
            
            # List all blobs in the container
            blob_list = container_client.list_blobs()
            for blob in blob_list:
                print(f"Blob: {blob.name}")
                print(f"Size: {blob.size} bytes")
                print(f"Last Modified: {blob.last_modified}")
                print("-" * 20)
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    list_blob_files() 