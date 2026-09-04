import streamlit as st
import requests
import json
import os
import time

# Set up page config
st.set_page_config(
    page_title="Custom Chatbot",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Endpoint
API_URL = "http://127.0.0.1:8000"

# Custom Styling (Slate/Modern)
st.markdown("""
<style>
    .main {
        background-color: #f8fafc;
    }
    .stButton>button {
        border-radius: 6px;
    }
    .card {
        padding: 20px;
        border-radius: 8px;
        background-color: white;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        margin-bottom: 20px;
        border: 1px solid #e2e8f0;
    }
    .card-title {
        font-size: 14px;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 8px;
    }
    .card-value {
        font-size: 28px;
        color: #0f172a;
        font-weight: 700;
    }
    .source-tag {
        display: inline-block;
        padding: 3px 8px;
        font-size: 11px;
        border-radius: 4px;
        background-color: #f1f5f9;
        color: #334155;
        border: 1px solid #e2e8f0;
        margin-right: 5px;
        margin-top: 5px;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# State Management Initialization
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

# Helper for API requests
def api_request(method, endpoint, json_data=None, files=None, params=None):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data, files=files, params=params)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        else:
            return None
        
        if response.status_code == 401:
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()
            
        return response
    except Exception as e:
        st.error(f"API Connection Error: {e}")
        return None

# Render AUTHENTICATION PAGE
if not st.session_state.token:
    st.title("🏢 Enterprise Knowledge System")
    st.write("Please sign in or register to access the enterprise knowledge base chatbot.")
    
    auth_tab = st.tabs(["Login", "Register"])
    
    with auth_tab[0]:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_user")
        login_password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login", type="primary", use_container_width=True):
            if login_username and login_password:
                res = api_request("POST", "/login", json_data={"username": login_username, "password": login_password})
                if res and res.status_code == 200:
                    data = res.json()
                    st.session_state.token = data["access_token"]
                    st.session_state.user = data["user"]
                    st.success("Successfully logged in!")
                    st.rerun()
                elif res:
                    st.error(res.json().get("detail", "Failed to login."))
            else:
                st.warning("Please fill in all fields.")
                
    with auth_tab[1]:
        st.subheader("Register")
        reg_username = st.text_input("Username", key="reg_user")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_pass")
        reg_role = st.selectbox("Role", ["user", "admin"], help="First registered user automatically becomes Admin.")
        
        if st.button("Register", type="primary", use_container_width=True):
            if reg_username and reg_email and reg_password:
                if len(reg_password) < 4:
                    st.error("Password must be at least 4 characters long.")
                else:
                    res = api_request("POST", "/register", json_data={
                        "username": reg_username,
                        "email": reg_email,
                        "password": reg_password,
                        "role": reg_role
                    })
                    if res and res.status_code == 201:
                        data = res.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.user = data["user"]
                        st.success("Registration successful!")
                        st.rerun()
                    elif res:
                        err_detail = res.json().get("detail", "Failed to register.")
                        if isinstance(err_detail, list):
                            err_detail = "; ".join([e.get("msg", str(e)) for e in err_detail])
                        st.error(err_detail)
            else:
                st.warning("Please fill in all fields.")
    st.stop()

# LOGGED IN LAYOUT

# Sidebar Navigation
with st.sidebar:
    st.markdown(f"### 🏢 Enterprise Portal")
    st.write(f"Logged in as: **{st.session_state.user['username']}** ({st.session_state.user['role'].upper()})")
    st.divider()
    
    # Navigation list
    pages = ["Dashboard", "Chat", "Knowledge Base", "Upload Documents", "Profile"]
    selected_page = st.radio("Navigation", pages)
    st.session_state.page = selected_page
    
    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state.token = None
        st.session_state.user = None
        st.session_state.current_conversation_id = None
        st.session_state.chat_history = []
        st.rerun()


# PAGES IMPLEMENTATION

if st.session_state.page == "Dashboard":
    st.title("📊 Enterprise Analytics Dashboard")
    st.write("Welcome to the Knowledge Base Portal. Here's a quick look at your system metrics.")
    st.divider()
    
    # Fetch metrics
    docs_res = api_request("GET", "/documents")
    convs_res = api_request("GET", "/conversations")
    
    total_docs = 0
    indexed_docs = 0
    total_chunks = 0
    total_convs = 0
    
    if docs_res and docs_res.status_code == 200:
        docs = docs_res.json()
        total_docs = len(docs)
        indexed_docs = sum(1 for d in docs if d["status"] == "indexed")
        total_chunks = sum(d["total_chunks"] for d in docs)
        
    if convs_res and convs_res.status_code == 200:
        total_convs = len(convs_res.json())
        
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Total Documents</div>
            <div class="card-value">{total_docs}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Indexed Documents</div>
            <div class="card-value">{indexed_docs}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Total Chunks</div>
            <div class="card-value">{total_chunks}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Conversations</div>
            <div class="card-value">{total_convs}</div>
        </div>
        """, unsafe_allow_html=True)

    # Display system information
    st.subheader("System Access & Configuration")
    st.info("""
    - **RAG Engine**: Enabled via Agno (Phidata) & pgvector
    - **Base LLM**: OpenAI GPT (Configurable / Fallback to Gemini 2.5)
    - **Vector DB**: PostgreSQL with pgvector extension
    - **Uploader Limit**: 20MB / PDF files only (Admin restricted)
    """)


elif st.session_state.page == "Upload Documents":
    st.title("📤 Document Ingestion")
    st.write("Ingest enterprise PDF files into the system's vector database. (Admins only)")
    st.divider()
    
    if st.session_state.user["role"] != "admin":
        st.error("Access Denied: Only system administrators are authorized to upload or manage documents.")
    else:
        uploaded_file = st.file_uploader("Select a PDF document to ingest:", type=["pdf"])
        
        if uploaded_file is not None:
            st.write(f"Filename: `{uploaded_file.name}`")
            st.write(f"Size: `{uploaded_file.size / 1024 / 1024:.2f} MB`")
            
            if uploaded_file.size > 20 * 1024 * 1024:
                st.error("Error: Upload file exceeds maximum permitted size of 20 MB.")
            else:
                if st.button("Ingest and Process Document", type="primary"):
                    with st.spinner("Uploading and starting background indexing..."):
                        # Post file to endpoint
                        files = {"file": (uploaded_file.name, uploaded_file.read(), "application/pdf")}
                        res = api_request("POST", "/documents/upload", files=files)
                        
                        if res and res.status_code == 200:
                            st.success(f"Successfully uploaded and queued '{uploaded_file.name}' for indexing!")
                            st.info("The document is being processed in the background. Check 'Knowledge Base' to track status.")
                        elif res:
                            st.error(res.json().get("detail", "Ingestion failed."))


elif st.session_state.page == "Knowledge Base":
    st.title("📚 Corporate Knowledge Base")
    st.write("Browse, search, and manage corporate files loaded into the system's index.")
    st.divider()
    
    # Add simple semantic search
    search_query = st.text_input("🔍 Quick Semantic Search Across All Documents:")
    if search_query:
        with st.spinner("Searching..."):
            search_res = api_request("GET", "/search", params={"query": search_query})
            if search_res and search_res.status_code == 200:
                results = search_res.json()
                if results:
                    st.write(f"Found {len(results)} relevant sections:")
                    for idx, chunk in enumerate(results):
                        with st.expander(f"Chunk {idx+1}: {chunk['filename']} (Page {chunk['page_number']})"):
                            st.markdown(chunk["chunk_text"])
                else:
                    st.write("No matching documents found.")
        st.divider()

    # List uploaded documents
    st.subheader("Ingested Documents")
    docs_res = api_request("GET", "/documents")
    
    if docs_res and docs_res.status_code == 200:
        docs = docs_res.json()
        if not docs:
            st.info("No documents are currently indexed. Please upload some PDFs first.")
        else:
            for doc in docs:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 2])
                    with col1:
                        st.write(f"📄 **{doc['original_name']}**")
                        st.caption(f"Uploaded by: {doc['uploaded_by']} | Date: {doc['upload_date'][:10]}")
                    with col2:
                        status_color = "🟢" if doc['status'] == "indexed" else "🟡" if doc['status'] == "processing" else "🔴"
                        st.write(f"{status_color} {doc['status'].upper()}")
                        st.caption(f"Pages: {doc['total_pages']} | Chunks: {doc['total_chunks']}")
                    
                    with col3:
                        if st.session_state.user["role"] == "admin":
                            if st.button("Re-index", key=f"reindex_{doc['id']}"):
                                with st.spinner("Queueing re-indexing..."):
                                    re_res = api_request("POST", f"/documents/reindex/{doc['id']}")
                                    if re_res and re_res.status_code == 200:
                                        st.success("Re-indexing started!")
                                        time.sleep(1)
                                        st.rerun()
                    with col4:
                        if st.session_state.user["role"] == "admin":
                            if st.button("Delete Document", key=f"del_{doc['id']}", type="secondary"):
                                with st.spinner("Deleting document..."):
                                    del_res = api_request("DELETE", f"/documents/{doc['id']}")
                                    if del_res and del_res.status_code == 200:
                                        st.success("Successfully deleted!")
                                        time.sleep(1)
                                        st.rerun()
                st.divider()


elif st.session_state.page == "Chat":
    st.title("💬 Enterprise Knowledge Assistant")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Conversations")
        
        # New chat button
        if st.button("➕ New Conversation", use_container_width=True):
            st.session_state.current_conversation_id = None
            st.session_state.chat_history = []
            st.rerun()
            
        st.divider()
        
        # Load conversation list
        conv_res = api_request("GET", "/conversations")
        if conv_res and conv_res.status_code == 200:
            conversations = conv_res.json()
            for c in conversations:
                label = f"Chat #{c['id']} ({c['created_at'][:10]})"
                
                # Active selection highlight
                is_selected = (st.session_state.current_conversation_id == c["id"])
                
                if st.button(label, key=f"select_conv_{c['id']}", use_container_width=True, type="primary" if is_selected else "secondary"):
                    st.session_state.current_conversation_id = c["id"]
                    
                    # Fetch conversation messages
                    detail_res = api_request("GET", f"/conversations/{c['id']}")
                    if detail_res and detail_res.status_code == 200:
                        st.session_state.chat_history = detail_res.json()["messages"]
                    st.rerun()
                    
    with col2:
        # Main chat window
        st.subheader("Chat Assistant")
        st.caption("Ask questions about any ingested PDFs. Response relies completely on retrieved knowledge.")
        st.divider()
        
        # Display history
        for msg in st.session_state.chat_history:
            role_label = "🧑‍💻 User" if msg["role"] == "user" else "🤖 Assistant"
            with st.chat_message(msg["role"]):
                st.markdown(f"**{role_label}**")
                st.markdown(msg["content"])
                
        # Handle new user input
        user_input = st.chat_input("Ask a question...")
        
        if user_input:
            # Append user message immediately
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            with st.chat_message("user"):
                st.markdown("**🧑‍💻 User**")
                st.markdown(user_input)
                
            with st.chat_message("assistant"):
                st.markdown("**🤖 Assistant**")
                
                with st.spinner("Consulting Corporate Knowledge Base..."):
                    payload = {"message": user_input}
                    if st.session_state.current_conversation_id:
                        payload["conversation_id"] = st.session_state.current_conversation_id
                        
                    res = api_request("POST", "/chat", json_data=payload)
                    
                    if res and res.status_code == 200:
                        data = res.json()
                        st.session_state.current_conversation_id = data["conversation_id"]
                        answer = data["answer"]
                        sources = data["sources"]
                        
                        st.markdown(answer)
                        
                        # Display sources
                        if sources:
                            st.write("**Sources:**")
                            for src in sources:
                                st.markdown(f"<span class='source-tag'>📄 {src['filename']} - Page {src['page_number']}</span>", unsafe_allow_html=True)
                        
                        # Add answer to local history
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    else:
                        st.error("Failed to generate response. Please ensure knowledge base is populated or check server logs.")
            st.rerun()


elif st.session_state.page == "Profile":
    st.title("👤 User Profile & Settings")
    st.write("Manage user parameters and system options.")
    st.divider()
    
    st.subheader("Account Details")
    st.write(f"- **Username**: `{st.session_state.user['username']}`")
    st.write(f"- **Email**: `{st.session_state.user['email']}`")
    st.write(f"- **Role Privilege**: `{st.session_state.user['role'].upper()}`")
    
    st.divider()
    st.subheader("Enterprise Configured Limits")
    st.write("- **Ingestion Size Limit**: `20 MB`")
    st.write("- **Permitted Ingestion Format**: `PDF Only`")
    st.write("- **Embedding Dimension**: `1536`")
    st.write("- **Vector Cosine Retrieval Count**: `5 Chunks`")
