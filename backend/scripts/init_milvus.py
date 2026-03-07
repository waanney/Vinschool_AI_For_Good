"""
Initialization script for Milvus collections.
Run this to set up the vector database.
"""

import asyncio
from database.milvus_client import milvus_client
from utils.logger import logger


async def init_milvus():
    """Initialize Milvus collections."""
    logger.info("Initializing Milvus collections...")
    
    # Create main document collection
    collection = milvus_client.create_document_collection("documents")
    logger.info(f"Created collection: {collection.name}")

    # Create grading results collection
    grading_col = milvus_client.create_grading_collection("grading_results")
    logger.info(f"Created collection: {grading_col.name}")
    
    logger.info("Milvus initialization complete!")


if __name__ == "__main__":
    asyncio.run(init_milvus())
