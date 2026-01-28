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
from utils.logger import logger

router = APIRouter()


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


class HomeworkSubmissionResponse(BaseModel):
    """Response for homework submission."""
    success: bool
    assignment_id: str
    message: str
    score: Optional[float] = None
    feedback: Optional[str] = None


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
