"""
Simple test script to debug embedding generation.
"""

import asyncio
from utils.embeddings import chunk_text, generate_embeddings
from utils.logger import logger


async def test_embeddings():
    test_text = """
# Test Content

This is a test document to verify chunking and embedding generation.
We want to make sure that the number of chunks equals the number of embeddings.
"""
    
    logger.info(f"Original text length: {len(test_text)} chars")
    
    # Chunk the text
    chunks = chunk_text(test_text, chunk_size=100, overlap=20)
    logger.info(f"Number of chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        logger.info(f"  Chunk {i}: {len(chunk)} chars - '{chunk[:50]}...'")
    
    # Generate embeddings
    embeddings = await generate_embeddings(chunks)
    logger.info(f"Number of embeddings: {len(embeddings)}")
    logger.info(f"Embeddings type: {type(embeddings)}")
    
    if len(embeddings) > 0:
        logger.info(f"First embedding type: {type(embeddings[0])}")
        logger.info(f"First embedding length: {len(embeddings[0])}")
    
    # Check if lengths match
    if len(chunks) == len(embeddings):
        logger.info("✓ SUCCESS: Chunks and embeddings have matching lengths!")
    else:
        logger.error(f"✗ ERROR: Length mismatch! chunks={len(chunks)}, embeddings={len(embeddings)}")


if __name__ == "__main__":
    asyncio.run(test_embeddings())
