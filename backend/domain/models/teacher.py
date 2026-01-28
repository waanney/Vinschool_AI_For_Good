"""
Teacher domain model.
Represents a teacher entity in the system.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID, uuid4


class TeacherId:
    """Value object for Teacher ID."""
    
    def __init__(self, value: UUID):
        self._value = value
    
    @classmethod
    def generate(cls) -> "TeacherId":
        """Generate a new teacher ID."""
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> "TeacherId":
        """Create TeacherId from string."""
        return cls(UUID(value))
    
    @property
    def value(self) -> UUID:
        return self._value
    
    def __str__(self) -> str:
        return str(self._value)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, TeacherId):
            return False
        return self._value == other._value
    
    def __hash__(self) -> int:
        return hash(self._value)


class Teacher(BaseModel):
    """
    Teacher entity.
    Represents a teacher in the educational system.
    """
    
    id: UUID = Field(default_factory=uuid4)
    teacher_code: str = Field(..., description="School teacher code")
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    subject: str = Field(..., description="Primary subject taught")
    classes: list[str] = Field(default_factory=list, description="Classes taught")
    
    # Preferences
    notification_preferences: dict[str, bool] = Field(
        default_factory=lambda: {
            "email_on_question": True,
            "email_on_grading_complete": False,
            "daily_summary": True
        }
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "teacher_code": "GV2024001",
                "full_name": "Trần Thị B",
                "email": "teacher@vinschool.edu.vn",
                "subject": "Mathematics",
                "classes": ["9A1", "9A2", "10B1"]
            }
        }
    
    def add_class(self, class_name: str) -> None:
        """Add a class to teacher's assignments."""
        if class_name not in self.classes:
            self.classes.append(class_name)
            self.updated_at = datetime.utcnow()
    
    def remove_class(self, class_name: str) -> None:
        """Remove a class from teacher's assignments."""
        if class_name in self.classes:
            self.classes.remove(class_name)
            self.updated_at = datetime.utcnow()
    
    def update_notification_preference(self, key: str, value: bool) -> None:
        """Update notification preferences."""
        self.notification_preferences[key] = value
        self.updated_at = datetime.utcnow()
