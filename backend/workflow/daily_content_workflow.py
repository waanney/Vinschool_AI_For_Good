"""
Daily Content Processing Workflow.
Orchestrates the flow from teacher upload to student content delivery.
"""

from typing import List
from datetime import datetime

from domain.models.document import Document, DocumentType
from agents.content_processor.agent import ContentProcessorAgent
from agents.teaching_assistant.agent import TeachingAssistantAgent, SummaryRequest
from utils.logger import logger


class DailyContentWorkflow:
    """
    Workflow for processing daily educational content.
    
    Flow:
    1. Teacher uploads materials
    2. Content is processed and embedded
    3. Summary is generated for students/parents
    4. Personalized exercises are created (optional)
    5. Content is distributed
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
    ) -> dict:
        """
        Process a single day's uploaded content.
        
        Args:
            document: Document metadata
            file_path: Path to uploaded file
            generate_summary: Whether to generate summary
            generate_exercises: Whether to generate exercises
            
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
            
            # Step 3: Generate personalized exercises (if requested)
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
