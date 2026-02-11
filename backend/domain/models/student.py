"""
Student domain model.
Represents a student entity with value objects following DDD principles.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID, uuid4


class StudentId:
    """Value object for Student ID."""
    
    def __init__(self, value: UUID):
        self._value = value
    
    @classmethod
    def generate(cls) -> "StudentId":
        """Generate a new student ID."""
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> "StudentId":
        """Create StudentId from string."""
        return cls(UUID(value))
    
    @property
    def value(self) -> UUID:
        return self._value
    
    def __str__(self) -> str:
        return str(self._value)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, StudentId):
            return False
        return self._value == other._value
    
    def __hash__(self) -> int:
        return hash(self._value)


class Student(BaseModel):
    """
    Student entity.
    Represents a student in the educational system.
    """
    
    id: UUID = Field(default_factory=uuid4)
    student_code: str = Field(..., description="School student code")
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    grade: int = Field(..., ge=1, le=12, description="Grade level 1-12")
    class_name: str = Field(..., description="Class identifier")
    
    # Learning profile
    learning_level: Optional[str] = Field(None, description="Current learning level assessment")
    strengths: list[str] = Field(default_factory=list, description="Academic strengths")
    weaknesses: list[str] = Field(default_factory=list, description="Areas needing improvement")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "student_code": "VS2024001",
                "full_name": "Nguyễn Văn A",
                "email": "student@vinschool.edu.vn",
                "grade": 9,
                "class_name": "9A1",
                "learning_level": "intermediate",
                "strengths": ["mathematics", "logical_thinking"],
                "weaknesses": ["essay_writing"]
            }
        }
    
    def update_learning_profile(
        self, 
        level: Optional[str] = None,
        strengths: Optional[list[str]] = None,
        weaknesses: Optional[list[str]] = None
    ) -> None:
        """Update student's learning profile."""
        if level is not None:
            self.learning_level = level
        if strengths is not None:
            self.strengths = strengths
        if weaknesses is not None:
            self.weaknesses = weaknesses
        self.updated_at = datetime.utcnow()
