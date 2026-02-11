"""
Document Repository implementation.
Handles document embeddings in Milvus and metadata in PostgreSQL.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from database.milvus_client import milvus_client
from domain.models.document import Document
from loguru import logger


class DocumentRepository:
    """
    Repository for document storage and retrieval.
    Integrates both Milvus (embeddings) and PostgreSQL (metadata).
    """
    
    def __init__(self):
        self.milvus = milvus_client
        self.collection_name = "documents"
    
    async def store_embeddings(
        self,
        document: Document,
        chunks: List[str],
        embeddings: List[List[float]],
    ) -> List[int]:
        """
        Store document chunks and embeddings in Milvus.
        
        Args:
            document: Document entity
            chunks: Text chunks
            embeddings: Corresponding embeddings
            
        Returns:
            List of Milvus IDs
        """
        # Prepare metadata for each chunk
        metadata_list = []
        for i in range(len(chunks)):
            metadata_list.append({
                "teacher_id": str(document.teacher_id),
                "class_name": document.class_name or "",
                "subject": document.subject,
                "grade": document.grade,
                "document_type": document.document_type,
                "title": document.title,
            })
        
        # Insert into Milvus
        milvus_ids = self.milvus.insert_embeddings(
            collection_name=self.collection_name,
            document_ids=[str(document.id)] * len(chunks),
            chunk_indices=list(range(len(chunks))),
            texts=chunks,
            embeddings=embeddings,
            metadata=metadata_list,
        )
        
        logger.info(f"Stored {len(chunks)} chunks for document {document.id}")
        
        return milvus_ids
    
    async def semantic_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        grade: Optional[int] = None,
        subject: Optional[str] = None,
        class_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search in document embeddings.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            grade: Filter by grade
            subject: Filter by subject
            class_name: Filter by class
            
        Returns:
            List of relevant document chunks with metadata
        """
        # Build filter expression
        filters = []
        if grade is not None:
            filters.append(f'metadata["grade"] == {grade}')
        if subject:
            filters.append(f'metadata["subject"] == "{subject}"')
        if class_name:
            filters.append(f'metadata["class_name"] == "{class_name}"')
        
        filter_expr = " and ".join(filters) if filters else None
        
        # Search
        results = self.milvus.search(
            collection_name=self.collection_name,
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filter_expr,
        )
        
        return results
    
    async def delete_document_embeddings(self, document_id: UUID) -> bool:
        """Delete all embeddings for a document."""
        try:
            self.milvus.delete_by_document_id(
                collection_name=self.collection_name,
                document_id=str(document_id),
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting embeddings for document {document_id}: {e}")
            return False
