import os
import shutil
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database.connection import get_db, engine, Base
from app.models.models import User, Document, DocumentChunk, Conversation, Message
from app.schemas.schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    DocumentResponse, ConversationResponse, MessageResponse,
    ChatRequest, ChatResponse, SearchResult
)
from app.utils.security import get_password_hash, verify_password, create_access_token, decode_access_token
from app.services.pdf_service import process_pdf_document
from app.services.vector_service import perform_vector_search
from app.services.agno_service import run_agent_query

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Directory for uploads
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Custom Chatbot", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators are allowed to perform this action.",
        )
    return user


# AUTHENTICATION ENDPOINTS

@app.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter((User.username == user_in.username) | (User.email == user_in.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or Email already registered",
        )
    
    # Create user
    # If there are no users, make the first registered user an Admin for ease of use
    first_user = db.query(User).count() == 0
    role = "admin" if first_user else user_in.role

    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hashed_password,
        role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Generate token
    access_token = create_access_token(data={"sub": db_user.username})
    user_resp = UserResponse(id=db_user.id, username=db_user.username, email=db_user.email, role=db_user.role)
    return Token(access_token=access_token, token_type="bearer", user=user_resp)

@app.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token
    access_token = create_access_token(data={"sub": user.username})
    user_resp = UserResponse(id=user.id, username=user.username, email=user.email, role=user.role)
    return Token(access_token=access_token, token_type="bearer", user=user_resp)


# DOCUMENT ENDPOINTS

@app.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)  # Only admin can upload
):
    # PDF only validation
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    # File size validation (Max 20MB)
    max_size = 20 * 1024 * 1024  # 20MB
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="File size exceeds the 20MB limit.")
    
    # Prevent duplicate upload for the same document if it's already processing
    existing_doc = db.query(Document).filter(
        Document.original_name == file.filename,
        Document.status == "processing"
    ).first()
    if existing_doc:
        raise HTTPException(status_code=400, detail="This document is already being processed.")

    # Save file
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    stored_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)

    # Create document database record
    db_doc = Document(
        filename=stored_filename,
        original_name=file.filename,
        uploaded_by=current_user.username,
        status="processing"
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # Trigger background PDF processing
    background_tasks.add_task(process_pdf_document, db, file_path, db_doc.id)

    return db_doc

@app.get("/documents", response_model=List[DocumentResponse])
def get_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Document).order_by(Document.upload_date.desc()).all()

@app.delete("/documents/{id}")
def delete_document(id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # Delete local file if it exists
    file_path = os.path.join(UPLOAD_DIR, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.delete(doc)
    db.commit()
    return {"message": f"Successfully deleted document {id}"}

@app.post("/documents/reindex/{id}", response_model=DocumentResponse)
def reindex_document(
    id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    if doc.status == "processing":
        raise HTTPException(status_code=400, detail="Document is already processing.")

    
    # Clean existing chunks
    db.query(DocumentChunk).filter(DocumentChunk.document_id == id).delete()
    doc.status = "processing"
    doc.total_chunks = 0
    db.commit()
    
    file_path = os.path.join(UPLOAD_DIR, doc.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Original file is missing from server storage.")

    # Trigger background processing
    background_tasks.add_task(process_pdf_document, db, file_path, doc.id)
    return doc


# KNOWLEDGE BASE SEARCH

@app.get("/search", response_model=List[SearchResult])
def search_knowledge_base(query: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not query.strip():
        return []
    
    search_results = perform_vector_search(db, query, limit=5)
    
    results = []
    for chunk, filename in search_results:
        # Distance to similarity (rough mapping)
        similarity = 1.0 - (chunk.embedding if hasattr(chunk, 'embedding') else 0) # pgvector handled similarity
        results.append(SearchResult(
            document_id=chunk.document_id,
            filename=filename,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            chunk_text=chunk.chunk_text,
            similarity=similarity
        ))
    return results


# CHAT MODULE

@app.post("/chat", response_model=ChatResponse)
def chat_with_bot(request: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversation_id = request.conversation_id
    
    # If no conversation_id, create a new conversation
    if not conversation_id:
        conversation = Conversation(user_id=current_user.id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        conversation_id = conversation.id
    else:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")

    # Save user message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()

    # Perform vector search
    relevant_chunks = perform_vector_search(db, request.message, limit=5)
    
    # Gather conversation history (last 6 messages) for context
    history_msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.desc())
        .limit(6)
        .all()
    )
    history_msgs.reverse()  # chronological order
    
    history_list = [{"role": msg.role, "content": msg.content} for msg in history_msgs if msg.id != user_msg.id]

    # Run Agno Agent query
    answer = run_agent_query(relevant_chunks, request.message, history_list)

    # Save Assistant message
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=answer
    )
    db.add(assistant_msg)
    db.commit()

    # Construct source references
    sources_set = set()
    sources = []
    for chunk, filename in relevant_chunks:
        src = (filename, chunk.page_number)
        if src not in sources_set:
            sources_set.add(src)
            sources.append({"filename": filename, "page_number": chunk.page_number})

    return ChatResponse(
        conversation_id=conversation_id,
        answer=answer,
        sources=sources
    )

@app.get("/conversations", response_model=List[ConversationResponse])
def get_conversations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )

@app.get("/conversations/{id}", response_model=ConversationResponse)
def get_conversation_by_id(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conv = db.query(Conversation).filter(Conversation.id == id, Conversation.user_id == current_user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conv
