"""
Reset Milvus collection with new configuration.
Drops existing collection and recreates with correct dimension.
"""

import asyncio
from database.milvus_client import milvus_client
from pymilvus import utility
from utils.logger import logger


async def reset_milvus():
    """Drop and recreate Milvus collection."""
    collection_name = "vinschool_documents"
    
    logger.info("Resetting Milvus collections...")
    
    # Drop existing collection if it exists
    if utility.has_collection(collection_name, using=milvus_client.alias):
        logger.info(f"Dropping existing collection: {collection_name}")
        utility.drop_collection(collection_name, using=milvus_client.alias)
        logger.info(f"✓ Dropped collection: {collection_name}")
    else:
        logger.info(f"Collection {collection_name} does not exist yet")
    
    # Create new collection with updated schema
    logger.info("Creating new collection with updated schema...")
    collection = milvus_client.create_document_collection("documents")
    logger.info(f"✓ Created collection: {collection.name}")
    logger.info(f"Collection ready with embedding dimension: 3072")
    
    logger.info("\n" + "="*60)
    logger.info("Milvus reset complete!")
    logger.info("You can now run populate_mock_data.py")
    logger.info("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(reset_milvus())
