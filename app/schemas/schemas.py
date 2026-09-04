from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

# User schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(..., min_length=4, description="Password must be at least 4 characters long")
    role: Optional[str] = "user"  # Default is user, admin is allowed

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Document schemas
class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_name: str
    upload_date: datetime
    uploaded_by: str
    status: str
    total_pages: int
    total_chunks: int

    class Config:
        from_attributes = True

# Message schemas
class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True

# Conversation schemas
class ConversationResponse(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True

# Search and Chat schemas
class SearchResult(BaseModel):
    document_id: int
    filename: str
    page_number: int
    chunk_index: int
    chunk_text: str
    similarity: float

class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    message: str

class ChatResponse(BaseModel):
    conversation_id: int
    answer: str
    sources: List[dict]  # List of dicts with {"filename": str, "page_number": int}
