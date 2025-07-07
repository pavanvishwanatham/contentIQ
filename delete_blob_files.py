import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

def delete_blob_files(container_name: str, file_names: list):
    """
    Delete specific files from Azure Blob Storage container.
    
    Args:
        container_name (str): Name of the container
        file_names (list): List of file names to delete
    """
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(
            os.getenv('AZURE_CONNECTION_STRING')
        )
        
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Delete each file
        for file_name in file_names:
            try:
                # Get blob client
                blob_client = container_client.get_blob_client(file_name)
                
                # Delete the blob
                print(f"Deleting {file_name}...")
                blob_client.delete_blob()
                print(f"Successfully deleted {file_name}")
                
            except Exception as e:
                print(f"Error deleting {file_name}: {str(e)}")
                
    except Exception as e:
        print(f"Error connecting to Azure Storage: {str(e)}")

if __name__ == "__main__":
    # Files to delete
    files_to_delete = ["sample1.pdf", "sample2.pdf"]
    container_name = "contentiq"  # Your container name
    
    # Delete the files
    delete_blob_files(container_name, files_to_delete) 