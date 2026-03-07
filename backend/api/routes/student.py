"""
Student API endpoints.
Handles student-specific operations like asking questions and submitting homework.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from pydantic import BaseModel
from pathlib import Path
import aiofiles

from domain.models.assignment import Assignment
from workflow.question_answering_workflow import QuestionAnsweringWorkflow
from workflow.homework_grading_workflow import HomeworkGradingWorkflow, GradingCriteria
from workflow.practice_exercise_workflow import PracticeExerciseWorkflow
from utils.logger import logger

router = APIRouter()


# ===== Request / Response models =====


class QuestionRequest(BaseModel):
    """Request for asking a question."""
    student_id: str
    question: str
    grade: int
    subject: str
    class_name: Optional[str] = None


class QuestionResponse(BaseModel):
    """Response to a question."""
    answer: str
    confidence: float
    escalated: bool
    sources: List[str] = []


class StudentProfileRequest(BaseModel):
    """Request for creating / updating a student profile.

    The ``student_id`` must match the platform-prefixed ID used by the
    chat bot (e.g. ``gchat-users/107677…``).
    """
    student_id: str
    student_name: str
    grade: int = 4
    class_name: str = "4B5"
    subjects: List[str] = []
    strengths: List[str] = []
    weaknesses: List[str] = []
    learning_level: str = ""
    notes: str = ""


class StudentProfileResponse(BaseModel):
    """Response after creating / updating a student profile."""
    success: bool
    student_id: str
    message: str



class HomeworkSubmissionResponse(BaseModel):
    """Response for homework submission."""
    success: bool
    assignment_id: str
    message: str
    score: Optional[float] = None
    feedback: Optional[str] = None


class PracticeExerciseRequest(BaseModel):
    """Request for personalized practice exercises."""
    student_id: str
    grade: int
    subject: str
    class_name: Optional[str] = None
    num_exercises: int = 5


class WeakPointInfo(BaseModel):
    """Information about a detected weak point."""
    topic: str
    error_rate: float
    recent_mistakes: List[str]


class ExerciseInfo(BaseModel):
    """Information about a recommended exercise."""
    exercise_id: str
    title: str
    topic: str
    difficulty: str
    description: str
    max_score: float


class PracticeExerciseResponse(BaseModel):
    """Response with practice exercise recommendations."""
    student_id: str
    subject: str
    grade: int
    weak_points: List[WeakPointInfo]
    recommendations: List[ExerciseInfo]
    success: bool
    error: Optional[str] = None


@router.post("/question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question to the AI teaching assistant.
    
    The AI will:
    1. Search the knowledge base for relevant context
    2. Generate an answer if confident
    3. Escalate to teacher if not confident
    """
    try:
        workflow = QuestionAnsweringWorkflow()
        
        result = await workflow.handle_question(
            student_id=request.student_id,
            question=request.question,
            grade=request.grade,
            subject=request.subject,
            class_name=request.class_name,
        )
        
        return QuestionResponse(
            answer=result["answer"],
            confidence=result["confidence"],
            escalated=result["escalated"],
            sources=result["sources"],
        )
        
    except Exception as e:
        logger.error(f"Question handling failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/homework/submit", response_model=HomeworkSubmissionResponse)
async def submit_homework(
    assignment_id: str = Form(...),
    student_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    auto_grade: bool = Form(True),
):
    """
    Submit homework for grading.
    
    Supports:
    - File uploads (images with OCR)
    - Automatic AI grading
    - Feedback generation
    """
    try:
        # Save uploaded file if provided
        file_path = None
        if file:
            upload_dir = Path("uploads") / "homework" / student_id
            upload_dir.mkdir(parents=True, exist_ok=True)
            file_path = upload_dir / file.filename
            
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            logger.info(f"Saved homework submission: {file_path}")
        
        # TODO: Retrieve assignment from database
        # For now, create a mock assignment
        assignment = Assignment(
            id=UUID(assignment_id),
            title="Sample Assignment",
            teacher_id=UUID("00000000-0000-4000-8000-000000000001"),
            student_id=UUID(student_id),
            class_name="9A1",
            subject="Mathematics",
            max_score=100.0,
        )
        
        # Mark as submitted
        assignment.submit(file_path=str(file_path) if file_path else "")
        
        response_data = {
            "success": True,
            "assignment_id": assignment_id,
            "message": "Homework submitted successfully",
        }
        
        # Auto-grade if requested
        if auto_grade:
            # Create default rubric
            workflow = HomeworkGradingWorkflow()
            rubric = workflow.create_standard_rubric("Mathematics", "homework")
            
            grading_result = await workflow.grade_homework(
                assignment=assignment,
                rubric=rubric,
                submission_file_path=str(file_path) if file_path else None,
            )
            
            if grading_result["success"]:
                response_data["score"] = grading_result["score"]
                response_data["feedback"] = grading_result["feedback"]
                response_data["message"] = "Homework submitted and graded"
        
        return HomeworkSubmissionResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Homework submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/feedback/{assignment_id}")
async def get_feedback(assignment_id: str):
    """Get grading feedback for an assignment."""
    # TODO: Retrieve from database
    return {
        "assignment_id": assignment_id,
        "message": "Feedback retrieval not yet implemented",
    }


@router.post("/practice-request", response_model=PracticeExerciseResponse)
async def request_practice_exercises(request: PracticeExerciseRequest):
    """
    Request personalized practice exercises based on weak points.
    
    The AI will:
    1. Analyze student's past performance to detect weak points
    2. Select appropriate exercises from the teacher's pool
    3. Return targeted practice recommendations
    
    Example:
        ```
        POST /api/student/practice-request
        {
            "student_id": "uuid-here",
            "grade": 9,
            "subject": "Mathematics",
            "num_exercises": 5
        }
        ```
    """
    try:
        workflow = PracticeExerciseWorkflow()
        
        # TODO: Retrieve student's recent assignments from database
        # For now, we'll pass None which will trigger general exercise generation
        result = await workflow.handle_practice_request(
            student_id=request.student_id,
            grade=request.grade,
            subject=request.subject,
            class_name=request.class_name,
            num_exercises=request.num_exercises,
            recent_assignments=None,  # Will be populated from database in production
        )
        
        # Convert to response model
        weak_points = [
            WeakPointInfo(
                topic=wp["topic"],
                error_rate=wp["error_rate"],
                recent_mistakes=wp["recent_mistakes"],
            )
            for wp in result["weak_points"]
        ]
        
        recommendations = [
            ExerciseInfo(
                exercise_id=rec["exercise_id"],
                title=rec["title"],
                topic=rec["topic"],
                difficulty=rec["difficulty"],
                description=rec["description"],
                max_score=rec["max_score"],
            )
            for rec in result["recommendations"]
        ]
        
        return PracticeExerciseResponse(
            student_id=result["student_id"],
            subject=result["subject"],
            grade=result["grade"],
            weak_points=weak_points,
            recommendations=recommendations,
            success=result["success"],
            error=result.get("error"),
        )
        
    except Exception as e:
        logger.error(f"Practice request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Student Profile endpoints =====


@router.post("/profile", response_model=StudentProfileResponse)
async def create_or_update_profile(request: StudentProfileRequest):
    """
    Create or update a student profile in Milvus.

    The profile stores strengths, weaknesses, subjects, learning level,
    and other metadata used by the ``/hw`` command to generate
    personalised supplementary homework suggestions.

    If a profile with the same ``student_id`` already exists it will be
    replaced (upsert semantics).

    Example:
        ```
        POST /api/student/profile
        {
            "student_id": "gchat-users/107677372930172037429",
            "student_name": "Phan Khánh",
            "grade": 4,
            "class_name": "4B5",
            "subjects": ["Toán", "Tiếng Việt", "Tiếng Anh"],
            "strengths": ["Tính nhẩm nhanh", "Đọc hiểu tốt"],
            "weaknesses": ["Phân số", "Viết chính tả"],
            "learning_level": "Khá",
            "notes": ""
        }
        ```
    """
    try:
        from database.repositories.student_profile_repository import (
            store_student_profile,
        )

        ok = await store_student_profile(
            student_id=request.student_id,
            student_name=request.student_name,
            grade=request.grade,
            class_name=request.class_name,
            subjects=request.subjects,
            strengths=request.strengths,
            weaknesses=request.weaknesses,
            learning_level=request.learning_level,
            notes=request.notes,
        )

        if not ok:
            raise HTTPException(
                status_code=503,
                detail="Milvus is unavailable — could not store profile",
            )

        return StudentProfileResponse(
            success=True,
            student_id=request.student_id,
            message=f"Profile for {request.student_name} stored successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student profile creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{student_id:path}")
async def get_profile(student_id: str):
    """
    Retrieve a student profile by ``student_id``.

    The ``student_id`` is the platform-prefixed ID, e.g.
    ``gchat-users/107677372930172037429``.  Because the ID contains a
    slash the path parameter uses ``:path`` matching.
    """
    try:
        from database.repositories.student_profile_repository import (
            get_student_profile,
        )

        profile = await get_student_profile(student_id)
        if profile is None:
            raise HTTPException(
                status_code=404,
                detail=f"No profile found for student_id={student_id}",
            )
        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Student profile retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
