import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv() 

logger = logging.getLogger(__name__)

SQL_USER = os.getenv("SQL_USER", "ai_studio_app_user")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")
SQL_DB_NAME = os.getenv("SQL_DB_NAME", "cloud_sql_development_database")
SQL_HOST = os.getenv("SQL_HOST", "localhost")

# Build the connection URL
if SQL_HOST.startswith("/"):
    # Unix domain socket (Cloud Run/Cloud SQL Auth Proxy)
    DATABASE_URL = f"postgresql+psycopg2://{SQL_USER}:{SQL_PASSWORD}@/{SQL_DB_NAME}?host={SQL_HOST}"
else:
    # Standard TCP host
    DATABASE_URL = f"postgresql+psycopg2://{SQL_USER}:{SQL_PASSWORD}@{SQL_HOST}/{SQL_DB_NAME}"

logger.info(f"Connecting to database with URL format: postgresql+psycopg2://{SQL_USER}:***@/{SQL_DB_NAME}")

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
