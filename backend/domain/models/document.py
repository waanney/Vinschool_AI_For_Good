"""
Document domain model.
Represents educational content uploaded by teachers.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class DocumentType(str, Enum):
    """Types of educational documents."""
    LESSON_PLAN = "lesson_plan"
    PRESENTATION = "presentation"  # PPTX
    WORKSHEET = "worksheet"  # DOCX, PDF
    ASSIGNMENT = "assignment"
    RUBRIC = "rubric"
    READING_MATERIAL = "reading_material"
    IMAGE = "image"
    OTHER = "other"


class DocumentId:
    """Value object for Document ID."""
    
    def __init__(self, value: UUID):
        self._value = value
    
    @classmethod
    def generate(cls) -> "DocumentId":
        """Generate a new document ID."""
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> "DocumentId":
        """Create DocumentId from string."""
        return cls(UUID(value))
    
    @property
    def value(self) -> UUID:
        return self._value
    
    def __str__(self) -> str:
        return str(self._value)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, DocumentId):
            return False
        return self._value == other._value
    
    def __hash__(self) -> int:
        return hash(self._value)


class Document(BaseModel):
    """
    Document entity.
    Represents educational content with metadata and processing status.
    """
    
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, max_length=500)
    document_type: DocumentType
    file_path: str = Field(..., description="Storage path of the document")
    file_extension: str = Field(..., description="File extension (.pdf, .docx, etc.)")
    file_size_bytes: int = Field(..., ge=0)
    
    # Ownership
    teacher_id: UUID = Field(..., description="Teacher who uploaded the document")
    class_name: Optional[str] = Field(None, description="Associated class")
    subject: str = Field(..., description="Subject area")
    grade: int = Field(..., ge=1, le=12)
    
    # Content
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    summary: Optional[str] = Field(None, description="AI-generated summary")
    keywords: list[str] = Field(default_factory=list, description="Extracted keywords")
    
    # Vector storage
    is_embedded: bool = Field(default=False, description="Whether embeddings are generated")
    milvus_ids: list[int] = Field(default_factory=list, description="IDs in Milvus vector DB")
    
    # Metadata
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "title": "Unit 9: Addition and Subtraction of Fractions",
                "document_type": "presentation",
                "file_path": "/uploads/2024/01/unit9_fractions.pptx",
                "file_extension": ".pptx",
                "file_size_bytes": 1024000,
                "teacher_id": "123e4567-e89b-12d3-a456-426614174000",
                "class_name": "9A1",
                "subject": "Mathematics",
                "grade": 9
            }
        }
    
    def mark_as_embedded(self, milvus_ids: list[int]) -> None:
        """Mark document as embedded with vector IDs."""
        self.is_embedded = True
        self.milvus_ids = milvus_ids
        self.processed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def update_summary(self, summary: str, keywords: list[str]) -> None:
        """Update document summary and keywords."""
        self.summary = summary
        self.keywords = keywords
        self.updated_at = datetime.utcnow()
