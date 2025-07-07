import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import argparse
from pathlib import Path

def upload_to_blob(file_path: str, container_name: str):
    """
    Upload a file to Azure Blob Storage container.
    
    Args:
        file_path (str): Path to the file to upload
        container_name (str): Name of the container to upload to
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
        
        # Get the file name from the path
        file_name = os.path.basename(file_path)
        
        # Get blob client
        blob_client = container_client.get_blob_client(file_name)
        
        # Upload the file
        print(f"Uploading {file_name} to container {container_name}...")
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
            
        print(f"Successfully uploaded {file_name}")
        
    except Exception as e:
        print(f"Error uploading file: {str(e)}")

def upload_directory(directory_path: str, container_name: str):
    """
    Upload all files from a directory to Azure Blob Storage container.
    
    Args:
        directory_path (str): Path to the directory containing files to upload
        container_name (str): Name of the container to upload to
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
        
        # Get all files in the directory
        files = [f for f in Path(directory_path).glob('**/*') if f.is_file()]
        
        print(f"Found {len(files)} files to upload...")
        
        # Upload each file
        for file_path in files:
            # Get the file name
            file_name = file_path.name
            
            # Get blob client
            blob_client = container_client.get_blob_client(file_name)
            
            # Upload the file
            print(f"Uploading {file_name}...")
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
                
        print("Successfully uploaded all files")
        
    except Exception as e:
        print(f"Error uploading files: {str(e)}")

def list_containers():
    """List all available containers in the storage account."""
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(
            os.getenv('AZURE_CONNECTION_STRING')
        )
        
        # List all containers
        containers = blob_service_client.list_containers()
        
        print("\nAvailable containers:")
        for container in containers:
            print(f"- {container.name}")
            
    except Exception as e:
        print(f"Error listing containers: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Upload files to Azure Blob Storage')
    parser.add_argument('--list', action='store_true', help='List all available containers')
    parser.add_argument('--file', type=str, help='Path to the file to upload')
    parser.add_argument('--dir', type=str, help='Path to the directory to upload')
    parser.add_argument('--container', type=str, help='Name of the container to upload to')
    
    args = parser.parse_args()
    
    if args.list:
        list_containers()
    elif args.file and args.container:
        upload_to_blob(args.file, args.container)
    elif args.dir and args.container:
        upload_directory(args.dir, args.container)
    else:
        print("Please provide either --list, or both --file/--dir and --container arguments")
        parser.print_help()

if __name__ == "__main__":
    main() 