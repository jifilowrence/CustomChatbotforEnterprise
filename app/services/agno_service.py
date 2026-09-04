import os
import logging
from typing import List, Dict, Any, Tuple
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from app.models.models import DocumentChunk

logger = logging.getLogger(__name__)

def get_agent_model() -> OpenAIChat:
    """
    Returns an OpenAIChat model configured correctly.
    Supports standard OpenAI key or falls back to Gemini OpenAI compatibility layer.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        model_id = os.getenv("CHAT_MODEL", "gpt-4o")
        logger.info(f"Agno Agent configured with standard OpenAI model: {model_id}")
        return OpenAIChat(id=model_id, api_key=openai_key)
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        model_id = os.getenv("CHAT_MODEL", "gemini-2.5-flash")
        logger.info(f"Agno Agent configured with Gemini OpenAI compatibility model: {model_id}")
        return OpenAIChat(
            id=model_id,
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    
    raise ValueError("Neither OPENAI_API_KEY nor GEMINI_API_KEY is configured in the environment.")

def run_agent_query(context_chunks: List[Tuple[DocumentChunk, str]], query: str, conversation_history: List[Dict[str, str]] = None) -> str:
    """
    Build context from retrieved chunks, inject into the , and query the Agno Agent.
    """
    # Format the context
    context_str = ""
    for idx, (chunk, filename) in enumerate(context_chunks):
        context_str += f"\n--- Source {idx + 1}: {filename} (Page {chunk.page_number}) ---\n"
        context_str += chunk.chunk_text + "\n"

    system_prompt = (
        "You are an Enterprise Knowledge Assistant.\n"
        "Answer ONLY using the retrieved knowledge provided in the context below.\n"
        "Never invent information or use pre-trained external knowledge.\n"
        "If the answer cannot be found in the provided context, clearly state that the "
        "knowledge base does not contain the requested information.\n"
        "Always answer professionally.\n"
        "Always include document references (filename and page number) when citing facts.\n"
        "Do not hallucinate sources."
    )

    # Build the full user message with context
    user_prompt = (
        f"Context:\n{context_str}\n\n"
        f"User Question: {query}\n"
    )

    # Initialize the Agno Agent with OpenAIChat model
    model = get_agent_model()
    
    # We can inject memory or pass the conversation history in the prompt.
    # In order to be robust and support custom conversation history cleanly,
    # we can format the conversation history directly into the context or prompt,
    # or let Agno's memory handle it. Let's pass the conversation history
    # to the agent or format it as part of the query.
    history_str = ""
    if conversation_history:
        history_str = "Conversation History:\n"
        for msg in conversation_history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            history_str += f"{role_label}: {msg['content']}\n"
        history_str += "\n"

    full_query = f"{history_str}{user_prompt}"

    agent = Agent(
        model=model,
        instructions=system_prompt,
        description="Enterprise Knowledge Assistant that answers questions using only document context.",
        markdown=True,
    )

    try:
        # Get response from Agno Agent
        response = agent.run(full_query)
        return response.content
    except Exception as e:
        logger.error(f"Error calling Agno Agent: {e}")
        return "Sorry, I encountered an error while processing your request. Please try again."
