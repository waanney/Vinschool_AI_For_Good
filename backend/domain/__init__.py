"""
Domain models package.
Implements Domain-Driven Design principles with entities and value objects.
"""

from domain.models.student import Student, StudentId
from domain.models.teacher import Teacher, TeacherId
from domain.models.document import Document, DocumentId, DocumentType
from domain.models.assignment import Assignment, AssignmentId, SubmissionStatus

__all__ = [
    "Student",
    "StudentId",
    "Teacher",
    "TeacherId",
    "Document",
    "DocumentId",
    "DocumentType",
    "Assignment",
    "AssignmentId",
    "SubmissionStatus",
]
