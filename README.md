# Custom Chatbot for Enterprise

An AI-powered enterprise chatbot that allows organizations to upload private documents and interact with them through a RAG-based conversational AI system.

## Key Features

* PDF document processing and text extraction
* RAG-based question answering
* Semantic vector search using PostgreSQL and pgvector
* Gemini-powered AI responses
* User authentication and role-based access control
* Admin and user roles

## Tech Stack

* **Frontend:** Streamlit
* **Backend:** FastAPI
* **AI:** Google Gemini, Agno
* **Database:** PostgreSQL, pgvector
* **Document Processing:** PyMuPDF
* **Authentication:** JWT, Passlib

## How It Works

```text
PDF Upload → Text Extraction → Chunking → Embeddings
                                      ↓
User Query → Vector Search → Relevant Context → Gemini → Response
```

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/custom-chatbot-for-enterprise.git
cd custom-chatbot-for-enterprise

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with your database and Gemini API credentials.

## Author

**Jifi**
