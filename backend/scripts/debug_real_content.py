"""
Debug script to test chunking and embedding with real document content.
"""

import asyncio
from utils.embeddings import chunk_text, generate_embeddings
from utils.logger import logger


# Real content from mock data
TEST_CONTENT = """
# Cộng và Trừ Phân Số

## 1. Cộng phân số cùng mẫu

Khi cộng hai phân số có cùng mẫu số, ta giữ nguyên mẫu số và cộng các tử số.

Công thức: a/c + b/c = (a+b)/c

Ví dụ: 2/7 + 3/7 = (2+3)/7 = 5/7
"""


async def test_real_content():
    logger.info(f"Testing with real content ({len(TEST_CONTENT)} chars)")
    
    # Chunk with same parameters as populate script
    chunks = chunk_text(TEST_CONTENT, chunk_size=1000, overlap=200)
    logger.info(f"Number of chunks: {len(chunks)}")
    
    for i, chunk in enumerate(chunks):
        logger.info(f"Chunk {i}: {len(chunk)} chars")
        logger.info(f"  Preview: {chunk[:100]}...")
    
    # Generate embeddings
    logger.info("\nGenerating embeddings...")
    embeddings = await generate_embeddings(chunks)
    
    logger.info(f"\nEmbeddings info:")
    logger.info(f"  Type: {type(embeddings)}")
    logger.info(f"  Length: {len(embeddings)}")
    
    if len(embeddings) > 0:
        logger.info(f"  First item type: {type(embeddings[0])}")
        if isinstance(embeddings[0], list):
            logger.info(f"  First embedding dims: {len(embeddings[0])}")
    
    # Check for match
    if len(chunks) == len(embeddings):
        logger.info(f"\n✓ SUCCESS: {len(chunks)} chunks = {len(embeddings)} embeddings")
    else:
        logger.error(f"\n✗ ERROR: {len(chunks)} chunks != {len(embeddings)} embeddings")
        logger.error("This is the bug causing Milvus insertion to fail!")


if __name__ == "__main__":
    asyncio.run(test_real_content())
