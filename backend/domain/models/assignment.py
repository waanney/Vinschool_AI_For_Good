"""
Assignment domain model.
Represents homework submissions and grading.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class SubmissionStatus(str, Enum):
    """Status of homework submission."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    GRADING = "grading"
    GRADED = "graded"
    RETURNED = "returned"


class AssignmentId:
    """Value object for Assignment ID."""
    
    def __init__(self, value: UUID):
        self._value = value
    
    @classmethod
    def generate(cls) -> "AssignmentId":
        """Generate a new assignment ID."""
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> "AssignmentId":
        """Create AssignmentId from string."""
        return cls(UUID(value))
    
    @property
    def value(self) -> UUID:
        return self._value
    
    def __str__(self) -> str:
        return str(self._value)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, AssignmentId):
            return False
        return self._value == other._value
    
    def __hash__(self) -> int:
        return hash(self._value)


class Assignment(BaseModel):
    """
    Assignment entity.
    Represents a homework assignment and student submission.
    """
    
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    
    # Assignment details
    teacher_id: UUID
    student_id: UUID
    class_name: str
    subject: str
    
    # Rubric and reference
    rubric_document_id: Optional[UUID] = Field(None, description="Reference rubric document")
    max_score: float = Field(default=100.0, ge=0)
    
    # Submission
    submission_file_path: Optional[str] = None
    submission_text: Optional[str] = Field(None, description="Extracted text from submission")
    submitted_at: Optional[datetime] = None
    status: SubmissionStatus = Field(default=SubmissionStatus.PENDING)
    
    # Grading
    ai_score: Optional[float] = Field(None, ge=0, description="AI-generated score")
    teacher_score: Optional[float] = Field(None, ge=0, description="Teacher override score")
    feedback: Optional[str] = Field(None, description="AI-generated feedback")
    teacher_feedback: Optional[str] = Field(None, description="Additional teacher feedback")
    graded_at: Optional[datetime] = None
    graded_by_teacher: bool = Field(default=False)
    
    # Metadata
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "title": "Unit 9 Practice: Fractions",
                "teacher_id": "123e4567-e89b-12d3-a456-426614174000",
                "student_id": "223e4567-e89b-12d3-a456-426614174000",
                "class_name": "9A1",
                "subject": "Mathematics",
                "max_score": 100.0,
                "status": "graded",
                "ai_score": 85.5,
                "feedback": "Good understanding of fractions. Minor calculation error in Q3."
            }
        }
    
    @property
    def final_score(self) -> Optional[float]:
        """Get final score (teacher score takes precedence)."""
        return self.teacher_score if self.teacher_score is not None else self.ai_score
    
    def submit(self, file_path: str, extracted_text: Optional[str] = None) -> None:
        """Mark assignment as submitted."""
        self.submission_file_path = file_path
        self.submission_text = extracted_text
        self.submitted_at = datetime.utcnow()
        self.status = SubmissionStatus.SUBMITTED
        self.updated_at = datetime.utcnow()
    
    def start_grading(self) -> None:
        """Mark assignment as being graded."""
        self.status = SubmissionStatus.GRADING
        self.updated_at = datetime.utcnow()
    
    def complete_ai_grading(self, score: float, feedback: str) -> None:
        """Complete AI grading."""
        self.ai_score = score
        self.feedback = feedback
        self.graded_at = datetime.utcnow()
        self.status = SubmissionStatus.GRADED
        self.updated_at = datetime.utcnow()
    
    def add_teacher_grading(self, score: float, feedback: Optional[str] = None) -> None:
        """Add or override with teacher grading."""
        self.teacher_score = score
        if feedback:
            self.teacher_feedback = feedback
        self.graded_by_teacher = True
        self.updated_at = datetime.utcnow()
    
    def return_to_student(self) -> None:
        """Mark assignment as returned to student."""
        self.status = SubmissionStatus.RETURNED
        self.updated_at = datetime.utcnow()
