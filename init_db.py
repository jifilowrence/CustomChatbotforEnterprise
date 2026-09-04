import os
import sys
from sqlalchemy import text
from app.database.connection import engine, Base
from app.models.models import User, Document, DocumentChunk, Conversation, Message

def init_db():
    print("Initializing Database...")
    try:
        # Create pgvector extension
        with engine.connect() as conn:
            # PostgreSQL requires superuser or admin with special privileges to create extensions.
            # In our Cloud SQL development instance, ai_studio_admin or app user should have privileges.
            print("Creating pgvector extension if not exists...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("Extension created successfully.")
    except Exception as e:
        print(f"Warning: Failed to create pgvector extension directly: {e}")
        print("Continuing with table creation...")

    try:
        print("Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully.")
    except Exception as e:
        print(f"Error creating tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
