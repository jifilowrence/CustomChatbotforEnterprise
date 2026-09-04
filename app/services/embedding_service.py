import os
import logging
from typing import List

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger(__name__)


def get_openai_client() -> OpenAI:
   
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not gemini_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured in the environment."
        )

    logger.info("Using Gemini OpenAI Compatibility Client")

    return OpenAI(
        api_key=gemini_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai"
    )


def get_embedding_model_name() -> str:
    """
    Get the configured Gemini embedding model.
    """

    return os.getenv(
        "EMBEDDING_MODEL",
        "gemini-embedding-001"
    )


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    """

    if not texts:
        return []

    try:
        client = get_openai_client()
        model = get_embedding_model_name()

        logger.info(
            f"Generating embeddings using model: {model}"
        )

        response = client.embeddings.create(
            input=texts,
            model=model,
            dimensions=1536
        )

        # Do NOT sort by index.
        # Gemini may return index=None through the OpenAI-compatible API.
        embeddings = [
            item.embedding
            for item in response.data
        ]

        # Make sure vectors match PostgreSQL Vector(1536)
        for embedding in embeddings:
            if len(embedding) != 1536:
                raise ValueError(
                    f"Expected 1536-dimensional embedding, "
                    f"but received {len(embedding)} dimensions."
                )

        logger.info(
            f"Successfully generated {len(embeddings)} embeddings"
        )

        return embeddings

    except Exception as e:
        logger.error(
            f"Error generating embeddings: {e}"
        )
        raise


def generate_query_embedding(text: str) -> List[float]:
    """
    Generate an embedding for a single query string.
    """

    embeddings = generate_embeddings([text])

    if not embeddings:
        raise ValueError(
            "Failed to generate query embedding."
        )

    return embeddings[0]