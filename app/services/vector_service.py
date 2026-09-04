import logging
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import DocumentChunk, Document
from app.services.embedding_service import generate_query_embedding

logger = logging.getLogger(__name__)

def perform_vector_search(db: Session, query: str, limit: int = 5) -> List[Tuple[DocumentChunk, str]]:
    """
    Generate query embedding and perform cosine similarity search
    using pgvector on PostgreSQL.
    Returns a list of tuples: (DocumentChunk, filename)
    """
    try:
        # Generate embedding
        query_vector = generate_query_embedding(query)
        
        # Query using pgvector cosine_distance
        results = (
            db.query(DocumentChunk, Document.filename)
            .join(Document, DocumentChunk.document_id == Document.id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(limit)
            .all()
        )
        return results
    except Exception as e:
        logger.error(f"Error during vector search: {e}")
        return []
