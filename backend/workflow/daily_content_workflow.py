"""
Daily Content Processing Workflow.
Orchestrates the flow from teacher upload to student content delivery,
including sending notifications to students (Google Chat) and parents (Zalo).
"""

from typing import List
from datetime import datetime

from domain.models.document import Document, DocumentType
from agents.content_processor.agent import ContentProcessorAgent
from agents.teaching_assistant.agent import TeachingAssistantAgent, SummaryRequest
from services.notification.notification_service import NotificationService
from services.notification.models import StudentInfo, ParentInfo
from utils.logger import logger


class DailyContentWorkflow:
    """
    Workflow for processing daily educational content.
    
    Flow:
    1. Teacher uploads materials
    2. Content is processed and embedded
    3. Summary is generated for students/parents
    4. Notifications are sent (Google Chat for students, Zalo for parents)
    5. Personalized exercises are created (optional)
    """
    
    def __init__(self):
        self.content_agent = ContentProcessorAgent()
        self.teaching_agent = TeachingAssistantAgent()
    
    async def process_daily_upload(
        self,
        document: Document,
        file_path: str,
        generate_summary: bool = True,
        generate_exercises: bool = True,
        send_notifications: bool = True,
    ) -> dict:
        """
        Process a single day's uploaded content.
        
        Args:
            document: Document metadata
            file_path: Path to uploaded file
            generate_summary: Whether to generate summary
            generate_exercises: Whether to generate exercises
            send_notifications: Whether to send notifications after summary
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Starting daily content workflow for: {document.title}")
        
        results = {
            "document_id": str(document.id),
            "processed_at": datetime.utcnow().isoformat(),
            "success": False,
            "processing_result": None,
            "summary": None,
            "notifications_sent": [],
            "exercises": [],
            "errors": [],
        }
        
        try:
            # Step 1: Process and embed document
            processing_result = await self.content_agent.run(
                document=document,
                file_path=file_path,
                use_ocr=False,
            )
            
            results["processing_result"] = processing_result.dict()
            
            if not processing_result.success:
                results["errors"].append(f"Processing failed: {processing_result.error}")
                return results
            
            # Step 2: Generate summary for students/parents
            if generate_summary and document.extracted_text:
                try:
                    summary_request = SummaryRequest(
                        content=document.extracted_text,
                        target_audience="students",
                        max_length=500,
                    )
                    summary = await self.teaching_agent.summarize_content(summary_request)
                    results["summary"] = summary
                except Exception as e:
                    logger.error(f"Summary generation failed: {e}")
                    results["errors"].append(f"Summary failed: {str(e)}")
            
            # Step 3: Send notifications with the AI summary
            if send_notifications and results["summary"]:
                try:
                    notification_results = await self._send_summary_notifications(
                        summary_text=results["summary"],
                    )
                    results["notifications_sent"] = notification_results
                except Exception as e:
                    logger.error(f"Notification sending failed: {e}")
                    results["errors"].append(f"Notifications failed: {str(e)}")
            
            # Step 4: Generate personalized exercises (if requested)
            if generate_exercises:
                try:
                    exercises = await self.teaching_agent.generate_personalized_exercises(
                        student_level="intermediate",  # Can be customized per student
                        subject=document.subject,
                        topic=document.title,
                        num_exercises=5,
                    )
                    results["exercises"] = exercises
                except Exception as e:
                    logger.error(f"Exercise generation failed: {e}")
                    results["errors"].append(f"Exercises failed: {str(e)}")
            
            results["success"] = True
            logger.info(f"Daily content workflow completed for: {document.title}")
            
        except Exception as e:
            logger.error(f"Daily content workflow failed: {e}")
            results["errors"].append(str(e))
        
        return results

    async def _send_summary_notifications(
        self,
        summary_text: str,
    ) -> list[dict]:
        """
        Send the AI-generated summary as notifications.

        The plain text summary is passed as-is to the NotificationService
        factory methods which send it to the appropriate channel:
        - Students get it via Google Chat
        - Parents get it via Zalo

        Returns:
            List of dicts with channel and success status.
        """
        date_str = datetime.now().strftime("%d/%m/%Y")
        notification_service = NotificationService()
        sent = []

        # Placeholder student/parent info — in production, iterate over class roster
        student = StudentInfo(student_id="student-001", name="Alex", grade="4", class_name="4B5")
        parent = ParentInfo(parent_id="parent-001", name="Phụ huynh Alex")

        # Send to students via Google Chat
        student_notification = notification_service.create_daily_summary_for_students(
            student=student,
            date=date_str,
            content=summary_text,
        )
        student_results = await notification_service.send(student_notification)
        for r in student_results:
            sent.append({"channel": r.channel.value, "success": r.success})

        # Send to parents via Zalo
        parent_notification = notification_service.create_daily_summary_for_parents(
            parent=parent,
            student=student,
            date=date_str,
            content=summary_text,
        )
        parent_results = await notification_service.send(parent_notification)
        for r in parent_results:
            sent.append({"channel": r.channel.value, "success": r.success})

        logger.info(f"Summary notifications sent: {sent}")
        return sent
    
    async def process_multiple_documents(
        self,
        documents: List[tuple[Document, str]],  # List of (document, file_path) tuples
    ) -> List[dict]:
        """Process multiple documents in batch."""
        results = []
        
        for document, file_path in documents:
            result = await self.process_daily_upload(document, file_path)
            results.append(result)
        
        logger.info(f"Batch processed {len(documents)} documents")
        
        return results
