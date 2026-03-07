"""
Reset Milvus collections with new configuration.
Drops existing collections and recreates with correct dimensions.
"""

import asyncio
from database.milvus_client import milvus_client
from pymilvus import utility
from utils.logger import logger


async def reset_milvus():
    """Drop and recreate Milvus collections."""
    collections = {
        "vinschool_documents": "documents",
        "vinschool_grading_results": "grading_results",
        "vinschool_student_profiles": "student_profiles",
        "vinschool_daily_lessons": "daily_lessons",
    }

    logger.info("Resetting Milvus collections...")

    for full_name, short_name in collections.items():
        # Drop existing collection if it exists
        if utility.has_collection(full_name, using=milvus_client.alias):
            logger.info(f"Dropping existing collection: {full_name}")
            utility.drop_collection(full_name, using=milvus_client.alias)
            logger.info(f"✓ Dropped collection: {full_name}")
        else:
            logger.info(f"Collection {full_name} does not exist yet")

    # Recreate collections
    logger.info("Creating collections with updated schema...")
    doc_col = milvus_client.create_document_collection("documents")
    logger.info(f"✓ Created collection: {doc_col.name}")

    grading_col = milvus_client.create_grading_collection("grading_results")
    logger.info(f"✓ Created collection: {grading_col.name}")

    profiles_col = milvus_client.create_student_profiles_collection("student_profiles")
    logger.info(f"✓ Created collection: {profiles_col.name}")

    lessons_col = milvus_client.create_daily_lessons_collection("daily_lessons")
    logger.info(f"✓ Created collection: {lessons_col.name}")

    logger.info("\n" + "="*60)
    logger.info("Milvus reset complete!")
    logger.info("You can now run populate_mock_data.py")
    logger.info("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(reset_milvus())
