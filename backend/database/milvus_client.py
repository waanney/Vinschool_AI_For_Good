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

    # ===== Daily Lessons Collection =====

    def create_daily_lessons_collection(
        self, collection_name: str = "daily_lessons"
    ) -> Optional[Collection]:
        """
        Create a collection for storing daily lesson content.

        Each row is one lesson chunk (one subject/topic per day) so
        ``/dailysum`` and ``/ask`` can retrieve the latest teaching
        material from Milvus instead of reading a static file.

        Schema fields:
            id          — auto-increment primary key
            date        — lesson date as ``YYYY-MM-DD``
            subject     — e.g. "Toán", "Khoa học"
            title       — lesson title / topic
            text        — full lesson content (embedded)
            embedding   — FLOAT_VECTOR of *text*
            metadata    — JSON (week, homework, notes, …)
        """
        if not self.connected:
            logger.warning("Milvus not connected — cannot create daily lessons collection")
            return None

        full_name = f"{settings.milvus_collection_prefix}_{collection_name}"

        if utility.has_collection(full_name, using=self.alias):
            logger.info(f"Daily lessons collection {full_name} already exists")
            return Collection(name=full_name, using=self.alias)

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="date", dtype=DataType.VARCHAR, max_length=20),
            FieldSchema(name="subject", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8000),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=settings.embedding_dimension,
            ),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Daily lesson content for /dailysum and /ask retrieval",
        )

        collection = Collection(name=full_name, schema=schema, using=self.alias)

        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128},
        }
        collection.create_index(field_name="embedding", index_params=index_params)

        logger.info(f"Created daily lessons collection: {full_name}")
        return collection

    def insert_daily_lesson(
        self,
        collection_name: str,
        date: str,
        subject: str,
        title: str,
        text: str,
        embedding: list[float],
        metadata: dict,
    ) -> list[int]:
        """
        Insert a daily lesson entry into Milvus.

        Returns:
            List of inserted primary-key IDs.
        """
        collection = self.get_collection(collection_name)
        if collection is None:
            collection = self.create_daily_lessons_collection(collection_name)
        if collection is None:
            logger.warning("Milvus not connected — cannot store daily lesson")
            return []

        entities = [
            [date],
            [subject],
            [title],
            [text],
            [embedding],
            [metadata],
        ]

        result = collection.insert(entities)
        collection.flush()

        logger.info(
            f"[MILVUS] Stored daily lesson: {subject} — {title} ({date}) "
            f"in {collection_name}"
        )
        return result.primary_keys

    def search_daily_lessons(
        self,
        collection_name: str,
        query_embedding: list[float],
        date: str | None = None,
        subject: str | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Search daily lessons by semantic similarity, optionally filtered
        by date and/or subject.

        Args:
            collection_name: Daily lessons collection name.
            query_embedding: Query vector.
            date: If provided, restrict to this date (``YYYY-MM-DD``).
            subject: If provided, restrict to this subject.
            top_k: Maximum results to return.

        Returns:
            List of lesson dicts.
        """
        collection = self.get_collection(collection_name)
        if collection is None:
            return []

        collection.load()

        # Build filter expression
        filters: list[str] = []
        if date:
            filters.append(f'date == "{date}"')
        if subject:
            filters.append(f'subject == "{subject}"')
        expr = " and ".join(filters) if filters else None

        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 16}},
            limit=top_k,
            expr=expr,
            output_fields=[
                "date", "subject", "title", "text", "metadata",
            ],
        )

        formatted = []
        for hits in results:
            for hit in hits:
                formatted.append({
                    "id": hit.id,
                    "similarity": hit.score,
                    "date": hit.entity.get("date"),
                    "subject": hit.entity.get("subject"),
                    "title": hit.entity.get("title"),
                    "text": hit.entity.get("text"),
                    "metadata": hit.entity.get("metadata", {}),
                })

        logger.info(
            f"[MILVUS] Daily lesson search returned {len(formatted)} results"
            + (f" for date={date}" if date else "")
            + (f" subject={subject}" if subject else "")
        )
        return formatted

    # ===== Student Profiles Collection =====

    def create_student_profiles_collection(
        self, collection_name: str = "student_profiles"
    ) -> Optional[Collection]:
        """
        Create a collection for storing student profile embeddings.

        Each row represents one student so the ``/hw`` command can
        retrieve the student's profile (strengths, weaknesses, subjects)
        and generate personalised homework suggestions.

        Schema fields:
            id              — auto-increment primary key
            student_id      — platform-prefixed ID (e.g. ``gchat-users/…``)
            student_name    — display name
            grade           — grade level (e.g. 4)
            class_name      — class identifier (e.g. "4B5")
            text            — human-readable profile summary (embedded)
            embedding       — FLOAT_VECTOR of *text*
            metadata        — JSON (subjects, strengths, weaknesses, …)
        """
        if not self.connected:
            logger.warning("Milvus not connected — cannot create student profiles collection")
            return None

        full_name = f"{settings.milvus_collection_prefix}_{collection_name}"

        if utility.has_collection(full_name, using=self.alias):
            logger.info(f"Student profiles collection {full_name} already exists")
            return Collection(name=full_name, using=self.alias)

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="student_id", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="student_name", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="grade", dtype=DataType.INT64),
            FieldSchema(name="class_name", dtype=DataType.VARCHAR, max_length=100),
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
            description="Student profile embeddings for personalised homework suggestions",
        )

        collection = Collection(name=full_name, schema=schema, using=self.alias)

        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128},
        }
        collection.create_index(field_name="embedding", index_params=index_params)

        logger.info(f"Created student profiles collection: {full_name}")
        return collection

    def insert_student_profile(
        self,
        collection_name: str,
        student_id: str,
        student_name: str,
        grade: int,
        class_name: str,
        text: str,
        embedding: list[float],
        metadata: dict,
    ) -> list[int]:
        """
        Insert or update a student profile in Milvus.

        If a profile with the same ``student_id`` already exists it is
        deleted first so the collection always has at most one row per
        student.

        Returns:
            List of inserted primary-key IDs.
        """
        collection = self.get_collection(collection_name)
        if collection is None:
            collection = self.create_student_profiles_collection(collection_name)
        if collection is None:
            logger.warning("Milvus not connected — cannot store student profile")
            return []

        # Upsert: delete existing profile for this student_id first
        try:
            collection.load()
            collection.delete(f'student_id == "{student_id}"')
            collection.flush()
        except Exception:
            pass  # collection may be empty / not loaded yet

        entities = [
            [student_id],
            [student_name],
            [grade],
            [class_name],
            [text],
            [embedding],
            [metadata],
        ]

        result = collection.insert(entities)
        collection.flush()

        logger.info(
            f"[MILVUS] Stored student profile for {student_name} "
            f"(grade {grade}, {class_name}) in {collection_name}"
        )
        return result.primary_keys

    def search_student_profiles(
        self,
        collection_name: str,
        query_embedding: list[float],
        student_id: str | None = None,
        top_k: int = 1,
    ) -> list[dict]:
        """
        Search student profiles by semantic similarity or exact student_id.

        Args:
            collection_name: Student profiles collection name.
            query_embedding: Query vector.
            student_id: If provided, restrict results to this student.
            top_k: Maximum results to return.

        Returns:
            List of profile dicts.
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
                "student_id", "student_name", "grade",
                "class_name", "text", "metadata",
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
                    "grade": hit.entity.get("grade"),
                    "class_name": hit.entity.get("class_name"),
                    "text": hit.entity.get("text"),
                    "metadata": hit.entity.get("metadata", {}),
                })

        logger.info(
            f"[MILVUS] Student profile search returned {len(formatted)} results"
            + (f" for student {student_id}" if student_id else "")
        )
        return formatted


# Global singleton instance
milvus_client = MilvusClient()


def get_milvus_client() -> MilvusClient:
    """Return the global ``MilvusClient`` singleton."""
    return milvus_client
