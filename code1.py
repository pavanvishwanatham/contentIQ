from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
import os
from azure.storage.blob import BlobServiceClient 
import glob



load_dotenv(override=True)

endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
index_name = os.getenv("AZURE_SEARCH_INDEX", "int-vec")
blob_container_name = os.getenv("BLOB_CONTAINER_NAME", "int-vec")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
storage_account_key = os.getenv("STORAGE_ACCOUNT_KEY")
storage_account_endpoint = os.getenv("STORAGE_ACCOUNT_ENDPOINT")
connection_string = os.getenv("AZURE_CONNECTION_STRING")
container_name = os.getenv("BLOB_CONTAINER_NAME", "int-vec")

def uploadFolderToBlobStorage(folder_path):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            full_file_path = os.path.join(root, file)
            
            relative_path = os.path.relpath(full_file_path, folder_path).replace("\\", "/")

            blob_client = blob_service_client.get_blob_client(container=container_name, blob=relative_path)
            with open(full_file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            print(f"✅ Uploaded: {relative_path}")


uploadFolderToBlobStorage("C:/Users/pavan/Downloads/qwert")





