import os
from dotenv import load_dotenv
from flask import request, redirect, abort, send_file
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
from flask import Flask
from io import BytesIO

# Load environment variables early so agent_backend can access them
load_dotenv()

import streamlit as st
from vectorize_documents import DocumentVectorizer
import base64
import agent_backend

# Set page config - must be called before any other Streamlit commands
st.set_page_config(
    page_title="Content IQ",
    page_icon="wocircle.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set header bar color to match sidebar
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] {
        background-color: #f0f2f6 !important;
    }
    .st-emotion-cache-18ni7ap {
        background-color: #f0f2f6 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize session state
if "interaction_history" not in st.session_state:
    st.session_state.interaction_history = []
if "user_input_box" not in st.session_state:
    st.session_state.user_input_box = ""

# Callback to handle submission and clear input
def submit_query():
    user_input = st.session_state.user_input_box
    # Only process non-empty input
    if user_input and user_input.strip():
        # Log user message
        st.session_state.interaction_history.append(("user", user_input))
        # Get response from backend
        response = agent_backend.run_agent(user_input)
        if isinstance(response, dict) and "response" in response:
            response = response["response"]
        # Log assistant response
        st.session_state.interaction_history.append(("assistant", response))
    # Clear the textarea
    st.session_state.user_input_box = ""

# Utility function for original UI background image
def get_base64_of_file(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Apply original UI styling
img_base64 = get_base64_of_file("ChatGPT Image Jun 9, 2025, 01_52_43 PM.png")

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(245,251,255,0.92), rgba(245,251,255,0.92)), url('data:image/png;base64,{img_base64}');
        background-size: cover;
    }}
    .chat-message.user {{
        background-color: #2b313e;
        color: white;
        padding: 0.75rem 1.2rem;
        border-radius: 16px 16px 4px 16px;
        margin-bottom: 0.5rem;
        max-width: 70%;
        margin-left: auto;
        margin-right: 0;
        text-align: right;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}
    .chat-message.assistant {{
        background-color: #e0e4ea;
        color: black;
        padding: 0.75rem 1.2rem;
        border-radius: 16px 16px 16px 4px;
        margin-bottom: 0.5rem;
        max-width: 70%;
        margin-right: auto;
        margin-left: 0;
        text-align: left;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# Original UI elements
col1, col2 = st.columns([1, 10])
with col1:
    st.image("wocircle.png", width=200)
with col2:
    st.title("Content IQ")

st.markdown(
    """
    This assistant helps you search and explore documents stored in Azure Blob Storage. Ask me to find specific documents or ask questions based on their content.
    """
)

st.header("Search/Ask Questions")
st.markdown("---")

# Sidebar settings
st.sidebar.header("Settings")
vectorizer = DocumentVectorizer()
try:
    containers = [c.name for c in vectorizer.blob_service_client.list_containers()]
    selected_container = st.sidebar.selectbox("Select Container", containers)
except Exception as e:
    st.error(f"Error connecting to Azure Storage: {str(e)}")
    st.stop()

# Sidebar interaction form
st.sidebar.markdown("---")
st.sidebar.header("Interact")
with st.sidebar.form(key="interaction_form"):
    user_input = st.text_area(
        "",
        placeholder="Enter your query or question...",
        key="user_input_box"
    )
    st.form_submit_button(
        "Submit",
        use_container_width=True,
        on_click=submit_query
    )

# Display chat history (latest at top)
history = st.session_state.interaction_history
for i in range(len(history) - 1, 0, -2):
    user_role, user_msg = history[i-1]
    assistant_role, assistant_msg = history[i]
    if user_role == 'user' and assistant_role == 'assistant':
        st.markdown(
            f"<div class='chat-message user'><strong>You:</strong> {user_msg}</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div class='chat-message assistant'>{assistant_msg}</div>",
            unsafe_allow_html=True
        )

app = Flask(__name__)

@app.route('/download')
def download_file():
    file_name = request.args.get('file')
    title = request.args.get('title', file_name)  # Use title if provided
    if not file_name:
        abort(400, "No file specified")

    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_BLOB_CONTAINER = "contentiq"

    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=AZURE_BLOB_CONTAINER, blob=file_name)
        blob_data = blob_client.download_blob().readall()
        return send_file(
            BytesIO(blob_data),
            as_attachment=True,
            download_name=title  # This sets the filename for the download
        )
    except Exception as e:
        print(f"Error downloading blob: {e}")
        abort(500, "Could not download file")
