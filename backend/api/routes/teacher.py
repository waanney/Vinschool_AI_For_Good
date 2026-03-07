"""
Teacher API endpoints.

Handles teacher-specific operations including:
- Document uploads and processing
- Daily lesson management (JSON and image-based via Gemini vision)
- Graded submission retrieval for the LMS dashboard
- Class reports
"""

from datetime import date as date_today
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import aiofiles
from pathlib import Path
import shutil

from domain.models.document import Document, DocumentType
from workflow.daily_content_workflow import DailyContentWorkflow
from utils.logger import logger

router = APIRouter()


# ===== Request / Response models =====


class UploadResponse(BaseModel):
    """Response for document upload."""
    success: bool
    document_id: str
    message: str
    summary: Optional[str] = None
    exercises: List[str] = []


class ReportRequest(BaseModel):
    """Request for generating reports."""
    class_name: str
    subject: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class DailyLessonRequest(BaseModel):
    """Request for uploading a daily lesson to Milvus.

    Each entry represents one subject's lesson content for a given day.
    Multiple entries can be posted for different subjects on the same date.
    """
    date: str
    subject: str
    title: str
    content: str
    homework: str = ""
    notes: str = ""


class DailyLessonResponse(BaseModel):
    """Response after uploading a daily lesson."""
    success: bool
    date: str
    subject: str
    message: str


class ImageLessonResponse(BaseModel):
    """Response after parsing a lesson image and storing it."""
    success: bool
    date: str
    subject: str
    title: str
    content: str
    homework: str
    notes: str
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    subject: str = Form(...),
    grade: int = Form(...),
    teacher_id: str = Form(...),
    class_name: Optional[str] = Form(None),
    document_type: str = Form("presentation"),
    generate_summary: bool = Form(True),
    generate_exercises: bool = Form(True),
):
    """
    Upload educational content for processing.

    This endpoint:
    1. Saves the uploaded file
    2. Processes and embeds content
    3. Generates summary and exercises
    4. Stores in vector database
    """
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        allowed_extensions = [".pdf", ".docx", ".pptx", ".jpg", ".jpeg", ".png"]

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )

        # Save uploaded file
        upload_dir = Path("uploads") / teacher_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / file.filename

        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        logger.info(f"Saved uploaded file: {file_path}")

        # Create document entity
        document = Document(
            title=title,
            document_type=DocumentType(document_type),
            file_path=str(file_path),
            file_extension=file_extension,
            file_size_bytes=len(content),
            teacher_id=UUID(teacher_id),
            class_name=class_name,
            subject=subject,
            grade=grade,
        )

        # Process through workflow
        workflow = DailyContentWorkflow()
        result = await workflow.process_daily_upload(
            document=document,
            file_path=str(file_path),
            generate_summary=generate_summary,
            generate_exercises=generate_exercises,
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {result.get('errors', [])}"
            )

        return UploadResponse(
            success=True,
            document_id=str(document.id),
            message="Document processed successfully",
            summary=result.get("summary"),
            exercises=result.get("exercises", []),
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        # Clean up file if it was saved
        if 'file_path' in locals() and Path(file_path).exists():
            Path(file_path).unlink()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{class_name}")
async def get_class_report(class_name: str, subject: Optional[str] = None):
    """Get progress report for a class."""
    # TODO: Implement report generation
    return {
        "class_name": class_name,
        "subject": subject,
        "message": "Report generation not yet implemented",
    }


@router.get("/questions/escalated")
async def get_escalated_questions(teacher_id: str):
    """Get questions that have been escalated to the teacher."""
    # TODO: Implement escalated question retrieval
    return {
        "teacher_id": teacher_id,
        "questions": [],
        "message": "Escalated question retrieval not yet implemented",
    }


# ===== Submission endpoints (for LMS teacher dashboard) =====


class SubmissionResponse(BaseModel):
    """A single graded submission."""
    id: str
    student_id: str
    student_name: str
    assignment_title: str
    subject: str
    score: float
    max_score: float
    feedback: str
    detailed_feedback: str = ""
    attachment_paths: list[str]
    details: dict
    graded_at: str
    is_viewed: bool


class SubmissionsListResponse(BaseModel):
    """List of submissions with unviewed count and grading thresholds."""
    submissions: list[SubmissionResponse]
    count: int
    unviewed_count: int
    low_grade_threshold: float


@router.get("/submissions", response_model=SubmissionsListResponse)
async def get_submissions():
    """
    Get all graded submissions for the teacher LMS dashboard.

    Returns submissions sorted by graded_at descending (newest first),
    along with unviewed_count for the notification badge.
    """
    from services.chat.submission_store import (
        get_submissions,
        get_unviewed_count,
    )
    from config.settings import get_settings

    app_settings = get_settings()
    submissions = get_submissions()
    return SubmissionsListResponse(
        submissions=[SubmissionResponse(**s) for s in submissions],
        count=len(submissions),
        unviewed_count=get_unviewed_count(),
        low_grade_threshold=app_settings.LOW_GRADE_THRESHOLD,
    )


@router.post("/submissions/{submission_id}/view")
async def mark_submission_viewed(submission_id: str):
    """
    Mark a submission as viewed by the teacher.

    This corresponds to the teacher clicking on a submission row
    in the LMS UI (grey → white background transition).
    """
    from services.chat.submission_store import mark_viewed

    found = mark_viewed(submission_id)
    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Submission {submission_id} not found",
        )
    return {"success": True, "submission_id": submission_id}


# ===== Daily Lesson endpoints =====


@router.post("/daily-lesson", response_model=DailyLessonResponse)
async def upload_daily_lesson(request: DailyLessonRequest):
    """
    Upload a daily lesson entry to Milvus.

    Each call stores one subject's content for a given date. Call
    multiple times for different subjects on the same day.

    The stored lessons are used by:
    - ``/dailysum`` — to generate a daily summary
    - ``/ask`` — to include lesson context in AI answers
    - ``load_lesson_context()`` — to replace the static ``data/lesson.txt``

    Example:
        ```
        POST /api/teacher/daily-lesson
        {
            "date": "2025-03-08",
            "subject": "Toán",
            "title": "Phân số — Cộng trừ phân số cùng mẫu",
            "content": "Kiến thức chính: Khi cộng (trừ) hai phân số cùng mẫu...",
            "homework": "Bài 1 trang 45 SGK, 5 bài tập phân số trong phiếu",
            "notes": "Hạn nộp: thứ Hai tuần sau"
        }
        ```
    """
    try:
        from database.repositories.daily_lesson_repository import (
            store_daily_lesson,
        )

        ok = await store_daily_lesson(
            date=request.date,
            subject=request.subject,
            title=request.title,
            content=request.content,
            homework=request.homework,
            notes=request.notes,
        )

        if not ok:
            raise HTTPException(
                status_code=503,
                detail="Milvus is unavailable — could not store lesson",
            )

        return DailyLessonResponse(
            success=True,
            date=request.date,
            subject=request.subject,
            message=f"Lesson '{request.title}' for {request.subject} on {request.date} stored successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Daily lesson upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-lessons/{date}")
async def get_daily_lessons(date: str):
    """
    Retrieve all lessons for a specific date.

    Args:
        date: Date in ``YYYY-MM-DD`` format.

    Returns:
        List of lesson entries for that date.
    """
    try:
        from database.repositories.daily_lesson_repository import (
            get_lessons_by_date,
        )

        lessons = await get_lessons_by_date(date)
        return {
            "date": date,
            "count": len(lessons),
            "lessons": lessons,
        }

    except Exception as e:
        logger.error(f"Daily lesson retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily-lesson/parse-image", response_model=ImageLessonResponse)
async def parse_lesson_image(
    file: UploadFile = File(...),
    date: str = Form(""),
    subject: str = Form(""),
):
    """
    Upload a lesson image, parse it with Gemini 2.5 Pro, and store
    the extracted content in the ``vinschool_daily_lessons`` Milvus
    collection.

    Accepts ``.jpg``, ``.jpeg``, or ``.png`` images.  Gemini reads
    the image and returns structured fields (subject, title, content,
    homework, notes) that are then embedded and inserted into Milvus.

    Form fields:
        file: The image file (required).
        date: Lesson date in ``YYYY-MM-DD`` format (defaults to today).
        subject: Optional subject hint to guide Gemini's parsing.

    Returns:
        The extracted lesson data along with a success flag.
    """
    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png"):
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in (".jpg", ".jpeg", ".png"):
            raise HTTPException(
                status_code=400,
                detail="Only .jpg, .jpeg, and .png images are supported.",
            )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Determine MIME type
    mime_type = file.content_type or "image/jpeg"
    if mime_type not in ("image/jpeg", "image/png"):
        mime_type = "image/jpeg"

    # Default date to today
    lesson_date = date.strip() if date.strip() else str(date_today.today())

    try:
        from utils.gemini_vision import parse_lesson_image as _parse_image

        parsed = await _parse_image(
            image_bytes=image_bytes,
            mime_type=mime_type,
            date_hint=lesson_date,
            subject_hint=subject.strip(),
        )
    except (ValueError, RuntimeError) as exc:
        logger.error(f"Image parsing failed: {exc}")
        raise HTTPException(status_code=502, detail=str(exc))

    # Store in Milvus
    try:
        from database.repositories.daily_lesson_repository import (
            store_daily_lesson,
        )

        ok = await store_daily_lesson(
            date=lesson_date,
            subject=parsed["subject"],
            title=parsed["title"],
            content=parsed["content"],
            homework=parsed["homework"],
            notes=parsed["notes"],
        )

        if not ok:
            raise HTTPException(
                status_code=503,
                detail="Milvus is unavailable — parsed content could not be stored.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Milvus storage failed after parsing: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return ImageLessonResponse(
        success=True,
        date=lesson_date,
        subject=parsed["subject"],
        title=parsed["title"],
        content=parsed["content"],
        homework=parsed["homework"],
        notes=parsed["notes"],
        message=(
            f"Lesson '{parsed['title']}' for {parsed['subject']} on "
            f"{lesson_date} parsed and stored successfully."
        ),
    )
