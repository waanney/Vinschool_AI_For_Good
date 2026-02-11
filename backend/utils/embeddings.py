"""
Embedding generation utilities.
Supports OpenAI and Google Gemini embedding models.
"""

from typing import List
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
import google.generativeai as genai

from config import settings

# Initialize clients based on provider
if settings.embedding_provider == "openai":
    openai.api_key = settings.openai_api_key
elif settings.embedding_provider == "google":
    if settings.gemini_api_key:
        genai.configure(api_key=settings.gemini_api_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for list of texts using configured provider.
    
    Args:
        texts: List of text strings
        
    Returns:
        List of embedding vectors
    """
    try:
        if settings.embedding_provider == "openai":
            return await _generate_openai_embeddings(texts)
        elif settings.embedding_provider == "google":
            return await _generate_gemini_embeddings(texts)
        else:
            raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
            
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise


async def _generate_openai_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using OpenAI API."""
    response = await openai.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    
    embeddings = [item.embedding for item in response.data]
    logger.info(f"Generated {len(embeddings)} embeddings using OpenAI {settings.embedding_model}")
    
    return embeddings


async def _generate_gemini_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using Google Gemini API."""
    # Gemini only supports models/embedding-001 for embeddings
    embeddings = []
    
    for text in texts:
        result = genai.embed_content(
            model="gemini-embedding-001",  # Fixed - Gemini's only supported embedding model
            content=text,
            task_type="retrieval_document",
        )
        embeddings.append(result['embedding'])
    
    logger.info(f"Generated {len(embeddings)} embeddings using Gemini text-embedding-004")
    
    return embeddings


async def generate_single_embedding(text: str) -> List[float]:
    """Generate embedding for a single text."""
    embeddings = await generate_embeddings([text])
    return embeddings[0]


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Input text
        chunk_size: Maximum characters per chunk
        overlap: Overlap characters between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            for sep in ['. ', '! ', '? ', '\n\n']:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1:
                    end = start + last_sep + len(sep)
                    break
        
        chunks.append(text[start:end].strip())
        start = end - overlap
    
    logger.debug(f"Split text into {len(chunks)} chunks")
    
    return chunks
