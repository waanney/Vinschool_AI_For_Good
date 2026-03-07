"""
Milvus Vector Database Client.
Manages connection and operations with Milvus for document embeddings
and grading result storage/retrieval.
"""

from typing import List, Optional, Dict, Any
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)
from loguru import logger

from config import settings


class MilvusClient:
    """
    Milvus client for vector database operations.
    Implements Singleton pattern for connection management.
    """
    
    _instance: Optional['MilvusClient'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.alias = "default"
            self.connected = False
            self.connect()
            MilvusClient._initialized = True
    
    def connect(self) -> None:
        """Establish connection to Milvus.

        Connection failure is **non-fatal**: the app will start without
        Milvus and all vector-DB operations will gracefully return empty
        results until the connection is restored.
        """
        try:
            if settings.milvus_uri:
                # Connect via URI and Token (Zilliz Cloud)
                connections.connect(
                    alias=self.alias,
                    uri=settings.milvus_uri,
                    token=settings.milvus_token,
                    secure=True
                )
                logger.info(f"Connected to Milvus via URI: {settings.milvus_uri}")
            else:
                # Connect via host and port (Local Milvus)
                connections.connect(
                    alias=self.alias,
                    host=settings.milvus_host,
                    port=settings.milvus_port,
                )
                logger.info(f"Connected to Milvus at {settings.milvus_host}:{settings.milvus_port}")
            self.connected = True
        except Exception as e:
            self.connected = False
            logger.error(f"Failed to connect to Milvus: {e}")
            logger.warning("Milvus is unavailable — vector-DB features will be disabled")
    
    def disconnect(self) -> None:
        """Close Milvus connection."""
        try:
            connections.disconnect(alias=self.alias)
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Error disconnecting from Milvus: {e}")
    
    def create_document_collection(self, collection_name: str) -> Optional[Collection]:
        """
        Create a collection for document embeddings.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Created collection instance, or ``None`` if Milvus is unavailable.
        """
        if not self.connected:
            logger.warning("Milvus not connected — cannot create document collection")
            return None

        full_name = f"{settings.milvus_collection_prefix}_{collection_name}"
        
        # Check if collection exists
        if utility.has_collection(full_name, using=self.alias):
            logger.info(f"Collection {full_name} already exists")
            return Collection(name=full_name, using=self.alias)
        
        # Define schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=5000),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=settings.embedding_dimension,
            ),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description=f"Document embeddings for {collection_name}",
        )
        
        # Create collection
        collection = Collection(
            name=full_name,
            schema=schema,
            using=self.alias,
        )
        
        logger.info(f"Created collection: {full_name}")
        
        # Create index for vector field
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128},
        }
        
        collection.create_index(
            field_name="embedding",
            index_params=index_params,
        )
        
        logger.info(f"Created index for collection: {full_name}")
        
        return collection
    
    def get_collection(self, collection_name: str) -> Optional[Collection]:
        """Get existing collection."""
        if not self.connected:
            return None

        full_name = f"{settings.milvus_collection_prefix}_{collection_name}"
        
        if not utility.has_collection(full_name, using=self.alias):
            logger.warning(f"Collection {full_name} does not exist")
            return None
        
        return Collection(name=full_name, using=self.alias)
    
    def insert_embeddings(
        self,
        collection_name: str,
        document_ids: List[str],
        chunk_indices: List[int],
        texts: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
    ) -> List[int]:
        """
        Insert document embeddings into collection.
        
        Args:
            collection_name: Target collection name
            document_ids: List of document UUIDs
            chunk_indices: Index of chunk within document
            texts: Text content
            embeddings: Vector embeddings
            metadata: Additional metadata (teacher_id, class, subject, etc.)
            
        Returns:
            List of inserted IDs
        """
        collection = self.get_collection(collection_name)
        if collection is None:
            collection = self.create_document_collection(collection_name)
        if collection is None:
            logger.warning("Milvus not connected — cannot insert embeddings")
            return []
        
        # Prepare data
        entities = [
            document_ids,
            chunk_indices,
            texts,
            embeddings,
            metadata,
        ]
        
        # Debug: Print entity structure
        logger.info(f"Inserting into {collection_name}:")
        logger.info(f"  document_ids: {len(document_ids)} items")
        logger.info(f"  chunk_indices: {len(chunk_indices)} items")
        logger.info(f"  texts: {len(texts)} items")
        logger.info(f"  embeddings: {len(embeddings)} items")
        if len(embeddings) > 0:
            logger.info(f"    First embedding len: {len(embeddings[0]) if isinstance(embeddings[0], list) else 'N/A'}")
        logger.info(f"  metadata: {len(metadata)} items")
        
        # Insert
        insert_result = collection.insert(entities)
        collection.flush()
        
        logger.info(
            f"Inserted {len(document_ids)} embeddings into {collection_name}, "
            f"IDs: {insert_result.primary_keys[:5]}..."
        )
        
        return insert_result.primary_keys
    
    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in collection.
        
        Args:
            collection_name: Collection to search
            query_embedding: Query vector
            top_k: Number of results
            filters: Optional filter expression (e.g., 'grade == 9')
            
        Returns:
            List of search results with scores
        """
        collection = self.get_collection(collection_name)
        if collection is None:
            logger.warning(f"Collection {collection_name} not found for search")
            return []
        
        # Load collection to memory
        collection.load()
        
        # Search parameters
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 16},
        }
        
        # Execute search
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=filters,
            output_fields=["document_id", "chunk_index", "text", "metadata"],
        )
        
        # Format results
        formatted_results = []
        for hits in results:
            for hit in hits:
                formatted_results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "document_id": hit.entity.get("document_id"),
                    "chunk_index": hit.entity.get("chunk_index"),
                    "text": hit.entity.get("text"),
                    "metadata": hit.entity.get("metadata", {}),
                })
        
        logger.info(f"Search returned {len(formatted_results)} results from {collection_name}")
        
        return formatted_results
    
    def delete_by_document_id(self, collection_name: str, document_id: str) -> int:
        """Delete all embeddings for a specific document."""
        collection = self.get_collection(collection_name)
        if collection is None:
            return 0
        
        expr = f'document_id == "{document_id}"'
        collection.delete(expr)
        collection.flush()
        
        logger.info(f"Deleted embeddings for document {document_id} from {collection_name}")
        
        return 1  # Milvus doesn't return delete count directly

    def create_grading_collection(self, collection_name: str = "grading_results") -> Collection:
        """
        Create a collection for storing grading result embeddings.

        Each row stores one graded submission so that students can later
        ``/ask`` about their own scores and Cô Hana can answer from Milvus.

        Schema fields:
            id              — auto-increment primary key
            student_id      — Google Chat user ID (for per-student filtering)
            student_name    — display name
            subject         — e.g. "Mathematics"
            score           — numeric score
            max_score       — maximum possible score
            text            — human-readable summary of the grading result
            embedding       — vector embedding of *text*
            metadata        — JSON (assignment_title, graded_at, feedback, …)
        """
        if not self.connected:
            logger.warning("Milvus not connected — cannot create grading collection")
            return None

        full_name = f"{settings.milvus_collection_prefix}_{collection_name}"

        if utility.has_collection(full_name, using=self.alias):
            logger.info(f"Grading collection {full_name} already exists")
            return Collection(name=full_name, using=self.alias)

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="student_id", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="student_name", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="subject", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="score", dtype=DataType.DOUBLE),
            FieldSchema(name="max_score", dtype=DataType.DOUBLE),
            FieldSchema(
                name="text",
                dtype=DataType.VARCHAR,
                max_length=5000,
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=settings.embedding_dimension,
            ),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Grading result embeddings for student Q&A retrieval",
        )

        collection = Collection(name=full_name, schema=schema, using=self.alias)

        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128},
        }
        collection.create_index(field_name="embedding", index_params=index_params)

        logger.info(f"Created grading collection: {full_name}")
        return collection

    def insert_grading_result(
        self,
        collection_name: str,
        student_id: str,
        student_name: str,
        subject: str,
        score: float,
        max_score: float,
        text: str,
        embedding: list[float],
        metadata: dict,
    ) -> list[int]:
        """
        Insert a single grading result into the grading collection.

        Returns:
            List of inserted primary-key IDs.
        """
        collection = self.get_collection(collection_name)
        if collection is None:
            collection = self.create_grading_collection(collection_name)
        if collection is None:
            logger.warning("Milvus not connected — cannot store grading result")
            return []

        entities = [
            [student_id],
            [student_name],
            [subject],
            [score],
            [max_score],
            [text],
            [embedding],
            [metadata],
        ]

        result = collection.insert(entities)
        collection.flush()

        logger.info(
            f"[MILVUS] Stored grading result for {student_name} "
            f"({score}/{max_score}) in {collection_name}"
        )
        return result.primary_keys

    def search_grading_results(
        self,
        collection_name: str,
        query_embedding: list[float],
        student_id: str | None = None,
        top_k: int = 3,
    ) -> list[dict]:
        """
        Search grading results by semantic similarity, optionally filtered
        to a specific student.

        Args:
            collection_name: Grading collection name.
            query_embedding: Query vector.
            student_id: If provided, restrict results to this student.
            top_k: Maximum results to return.

        Returns:
            List of dicts with score, text, and metadata.
        """
        collection = self.get_collection(collection_name)
        if collection is None:
            return []

        collection.load()

        expr = f'student_id == "{student_id}"' if student_id else None

        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 16}},
            limit=top_k,
            expr=expr,
            output_fields=[
                "student_id", "student_name", "subject",
                "score", "max_score", "text", "metadata",
            ],
        )

        formatted = []
        for hits in results:
            for hit in hits:
                formatted.append({
                    "id": hit.id,
                    "similarity": hit.score,
                    "student_id": hit.entity.get("student_id"),
                    "student_name": hit.entity.get("student_name"),
                    "subject": hit.entity.get("subject"),
                    "score": hit.entity.get("score"),
                    "max_score": hit.entity.get("max_score"),
                    "text": hit.entity.get("text"),
                    "metadata": hit.entity.get("metadata", {}),
                })

        logger.info(
            f"[MILVUS] Grading search returned {len(formatted)} results"
            + (f" for student {student_id}" if student_id else "")
        )
        return formatted


# Global singleton instance
milvus_client = MilvusClient()


def get_milvus_client() -> MilvusClient:
    """Return the global ``MilvusClient`` singleton."""
    return milvus_client
