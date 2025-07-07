##CONTENT IQ AGENT


A conversational AI agent powered by **LangGraph**, **Azure OpenAI**, and **Azure AI Search**. It intelligently handles small talk and seamlessly transitions to document search when asked about topics like “Power BI” or “project reports.”

---

## 🧠 How It Works

| Stage               | Description                                                                 |
|---------------------|-----------------------------------------------------------------------------|
| User Input          | Accepts user queries in natural language                                    |
| Input Router        | Classifies whether to chat or search documents                              |
| Conversation Node   | If chat, responds using Azure OpenAI's GPT                                  |
| Topic Extractor     | Extracts topic keywords for document search                                 |
| Azure AI Search     | Runs hybrid (vector + keyword) query on indexed blob docs                   |
| Results Formatter   | Formats document matches into clean Markdown-style response                 |

---

## 🔁 LangGraph Flow

![LangGraph Flowchart](langgraph_flowchart.png)

---

## 🚀 Quickstart

### 1. ✅ Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. 🔐 Setup Environment Variables

Create a `.env` file:

```dotenv
AZURE_ENDPOINT=...
AZURE_API_KEY=...
AZURE_SEARCH_ENDPOINT=...
AZURE_SEARCH_KEY=...
AZURE_SEARCH_INDEX=docindex
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_STORAGE_CONTAINER=...
```

### 3. 📦 Index Your PDFs/PPTs

```bash
python index_blob_docs.py
```

### 4. 💬 Start the Agent

```bash
python agent.py
```

---

## 📂 Folder Structure

| File                  | Purpose                                            |
|-----------------------|----------------------------------------------------|
| `agent.py`            | CLI interface and LangGraph agent runner          |
| `nodes.py`            | Node logic for chat, topic extraction, search     |
| `index_blob_docs.py`  | Indexes documents to Azure Cognitive Search       |
| `.env`                | Secure config (excluded from repo)                |
| `requirements.txt`    | Python dependencies                               |

---

## 🧪 Example Usage


You: Hi!
AI: Hello! 😊 How can I help you today?

You: Search for documents about Power BI
AI: 📚 Top Matching Documents
     🔹 PowerBI_Report.pdf
     🔹 Dashboard_Tutorial.pptx

You: Who are you?
AI: I'm your assistant powered by Azure OpenAI and LangGraph!


---

## 📊 Azure AI Search Index Design

| Field           | Type       | Searchable | Vector Field |
|----------------|------------|------------|--------------|
| id             | string     | No         | No           |
| title          | string     | Yes        | No           |
| content        | string     | Yes        | No           |
| content_vector | collection | No         | ✅ Yes (1536) |

---

## 🧠 Tech Stack

- 🧩 LangGraph: State machine orchestration
- 🌐 Azure OpenAI: GPT chat & embeddings
- 🔍 Azure Cognitive Search: Hybrid search
- ☁️ Azure Blob Storage: PDF/PPT document source

---

## 📌 Notes

- Uses `text-embedding-ada-002` for vector search
- Snippets are truncated to 500 characters
- Flowchart image auto-generated from `graphviz`
- GPT-4o for Agent Functions

---

Made with ❤️ by Devaamsh using LangGraph + Azure.
