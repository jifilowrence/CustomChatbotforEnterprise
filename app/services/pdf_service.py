import fitz  # PyMuPDF
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import Document, DocumentChunk
from app.services.embedding_service import generate_embeddings

logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> List[str]:
    """
    Split text into overlapping chunks of a specific size.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - chunk_overlap)
    
    return chunks

def process_pdf_document(db: Session, file_path: str, document_id: int) -> bool:
    """
    Process a PDF file: extract text page-by-page, chunk it,
    generate embeddings in batch, and save to the database.
    """
    try:
        # Fetch the document record
        doc_record = db.query(Document).filter(Document.id == document_id).first()
        if not doc_record:
            logger.error(f"Document with ID {document_id} not found.")
            return False

        doc_record.status = "processing"
        db.commit()

        # Open the PDF using PyMuPDF
        pdf = fitz.open(file_path)
        total_pages = len(pdf)
        doc_record.total_pages = total_pages
        db.commit()

        all_chunks_data = []
        chunk_index = 0

        # Process page by page
        for page_num in range(total_pages):
            page = pdf[page_num]
            text = page.get_text().strip()
            
            # Ignore empty pages
            if not text:
                continue

            # Split into overlapping chunks
            chunks = chunk_text(text, chunk_size=800, chunk_overlap=150)
            
            for chunk_text_segment in chunks:
                all_chunks_data.append({
                    "page_number": page_num + 1,  # 1-indexed page numbers
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text_segment
                })
                chunk_index += 1

        pdf.close()

        if not all_chunks_data:
            logger.warning(f"No text extracted from document ID {document_id}.")
            doc_record.status = "indexed"
            doc_record.total_chunks = 0
            db.commit()
            return True

        # Generate embeddings in batches of 16 for stability and performance
        batch_size = 16
        texts_to_embed = [item["chunk_text"] for item in all_chunks_data]
        embeddings = []

        for i in range(0, len(texts_to_embed), batch_size):
            batch_texts = texts_to_embed[i:i + batch_size]
            batch_embeddings = generate_embeddings(batch_texts)
            embeddings.extend(batch_embeddings)

        # Create DocumentChunk records
        for idx, chunk_data in enumerate(all_chunks_data):
            db_chunk = DocumentChunk(
                document_id=document_id,
                page_number=chunk_data["page_number"],
                chunk_index=chunk_data["chunk_index"],
                chunk_text=chunk_data["chunk_text"],
                embedding=embeddings[idx]
            )
            db.add(db_chunk)

        doc_record.total_chunks = len(all_chunks_data)
        doc_record.status = "indexed"
        db.commit()
        
        logger.info(f"Successfully indexed document ID {document_id}: {len(all_chunks_data)} chunks created.")
        return True

    except Exception as e:
        logger.error(f"Error processing PDF document ID {document_id}: {e}")
        try:
            db_rollback = db.query(Document).filter(Document.id == document_id).first()
            if db_rollback:
                db_rollback.status = "failed"
                db.commit()
        except Exception as rollback_err:
            logger.error(f"Failed to set status to failed: {rollback_err}")
        return False
