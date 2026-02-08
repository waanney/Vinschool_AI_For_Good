"""
Question Answering Workflow.
Handles student questions with automatic routing and escalation.
"""

from typing import Optional
from datetime import datetime

from agents.teaching_assistant.agent import (
    TeachingAssistantAgent,
    QuestionContext,
    AnswerResponse,
)
from config import settings
from utils.logger import logger


class QuestionAnsweringWorkflow:
    """
    Workflow for handling student questions.
    
    Flow:
    1. Student submits question
    2. AI searches knowledge base
    3. If confident → provide answer
    4. If not confident → escalate to teacher
    5. Log interaction for analytics
    """
    
    def __init__(self):
        self.teaching_agent = TeachingAssistantAgent()
        self.escalation_threshold = settings.teacher_escalation_threshold
    
    async def handle_question(
        self,
        student_id: str,
        question: str,
        grade: int,
        subject: str,
        class_name: Optional[str] = None,
    ) -> dict:
        """
        Handle a student question end-to-end.
        
        Args:
            student_id: Student ID
            question: Question text
            grade: Student grade level
            subject: Subject area
            class_name: Optional class identifier
            
        Returns:
            Dictionary with answer or escalation info
        """
        logger.info(f"Handling question from student {student_id}: {question[:100]}")
        
        result = {
            "student_id": student_id,
            "question": question,
            "timestamp": datetime.utcnow().isoformat(),
            "answer": None,
            "confidence": 0.0,
            "escalated": False,
            "escalation_reason": None,
            "sources": [],
        }
        
        try:
            # Create question context
            context = QuestionContext(
                question=question,
                student_id=student_id,
                grade=grade,
                subject=subject,
                class_name=class_name,
            )
            
            # Get answer from teaching assistant
            response: AnswerResponse = await self.teaching_agent.answer_question(context)
            
            # Update result
            result["answer"] = response.answer
            result["confidence"] = response.confidence
            result["sources"] = response.sources
            
            # Check if escalation is needed
            if response.escalate_to_teacher or response.confidence < self.escalation_threshold:
                result["escalated"] = True
                result["escalation_reason"] = response.reasoning
                
                logger.info(
                    f"Question escalated to teacher. "
                    f"Confidence: {response.confidence:.2f}, "
                    f"Reason: {response.reasoning}"
                )
            else:
                logger.info(
                    f"Question answered successfully. "
                    f"Confidence: {response.confidence:.2f}"
                )
            
        except Exception as e:
            logger.error(f"Error handling question: {e}")
            result["escalated"] = True
            result["escalation_reason"] = f"Error occurred: {str(e)}"
            result["answer"] = "Xin lỗi, đã có lỗi xảy ra. Câu hỏi của bạn đã được chuyển đến giáo viên."
        
        return result
    
    async def get_answer_for_teacher_review(
        self,
        student_id: str,
        question: str,
        grade: int,
        subject: str,
    ) -> dict:
        """
        Get AI-generated answer for teacher to review before sending to student.
        Used when teacher wants to verify AI response.
        """
        context = QuestionContext(
            question=question,
            student_id=student_id,
            grade=grade,
            subject=subject,
        )
        
        response = await self.teaching_agent.answer_question(context)
        
        return {
            "suggested_answer": response.answer,
            "confidence": response.confidence,
            "sources": response.sources,
            "reasoning": response.reasoning,
        }
