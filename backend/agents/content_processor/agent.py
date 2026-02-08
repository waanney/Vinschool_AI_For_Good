"""
Content Processor Agent.
Handles document upload, parsing, and embedding generation.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel

from agents.base.agent import BaseAgent, AgentConfig
from domain.models.document import Document, DocumentType
from database.repositories.document_repository import DocumentRepository
from utils.document_parser import DocumentParser
from utils.embeddings import generate_embeddings, chunk_text
from utils.logger import logger


class ProcessingResult(BaseModel):
    """Result of document processing."""
    success: bool
    document_id: str
    num_chunks: int
    milvus_ids: List[int] = []
    summary: Optional[str] = None
    keywords: List[str] = []
    error: Optional[str] = None


class ContentProcessorAgent(BaseAgent):
    """
    Content Processor Agent.
    
    Responsibilities:
    - Parse uploaded documents (PPTX, DOCX, PDF, images)
    - Extract text content
    - Generate embeddings
    - Store in Milvus vector database
    - Generate summaries and keywords
    """
    
    SYSTEM_PROMPT = """You are a content analysis assistant.
Your role is to:
1. Analyze educational documents
2. Extract key concepts and topics
3. Generate concise summaries
4. Identify important keywords

Focus on educational value and clarity."""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        super().__init__(config)
        self.parser = DocumentParser()
        self.document_repo = DocumentRepository()
        self._agent = self._create_agent(system_prompt=self.SYSTEM_PROMPT)
    
    async def process_document(
        self,
        document: Document,
        file_path: str,
        use_ocr: bool = False,
    ) -> ProcessingResult:
        """
        Process uploaded document end-to-end.
        
        Args:
            document: Document entity
            file_path: Path to uploaded file
            use_ocr: Whether to use OCR for PDFs/images
            
        Returns:
            Processing result with status and IDs
        """
        try:
            logger.info(f"Processing document: {document.title}")
            
            # Step 1: Parse document
            extracted_text = self.parser.parse_file(file_path, use_ocr=use_ocr)
            
            if not extracted_text:
                return ProcessingResult(
                    success=False,
                    document_id=str(document.id),
                    num_chunks=0,
                    error="No text could be extracted from document",
                )
            
            # Update document with extracted text
            document.extracted_text = extracted_text
            
            # Step 2: Generate summary and keywords
            summary, keywords = await self._analyze_content(extracted_text)
            document.update_summary(summary, keywords)
            
            # Step 3: Chunk text
            chunks = chunk_text(extracted_text, chunk_size=1000, overlap=200)
            
            # Step 4: Generate embeddings
            embeddings = await generate_embeddings(chunks)
            
            # Step 5: Store in Milvus
            milvus_ids = await self.document_repo.store_embeddings(
                document=document,
                chunks=chunks,
                embeddings=embeddings,
            )
            
            # Step 6: Update document status
            document.mark_as_embedded(milvus_ids)
            
            logger.info(
                f"Successfully processed document {document.id}: "
                f"{len(chunks)} chunks, {len(milvus_ids)} embeddings stored"
            )
            
            return ProcessingResult(
                success=True,
                document_id=str(document.id),
                num_chunks=len(chunks),
                milvus_ids=milvus_ids,
                summary=summary,
                keywords=keywords,
            )
            
        except Exception as e:
            logger.error(f"Error processing document {document.id}: {e}")
            return ProcessingResult(
                success=False,
                document_id=str(document.id),
                num_chunks=0,
                error=str(e),
            )
    
    async def _analyze_content(self, text: str) -> tuple[str, List[str]]:
        """
        Generate summary and extract keywords from text.
        
        Args:
            text: Document text
            
        Returns:
            Tuple of (summary, keywords)
        """
        try:
            prompt = f"""Analyze this educational content and provide:
1. A concise summary (max 200 words) in Vietnamese
2. A list of 5-10 key topics/keywords in Vietnamese

Content:
{text[:3000]}  # Limit to first 3000 chars

Format your response as:
SUMMARY:
[your summary]

KEYWORDS:
[keyword1, keyword2, ...]"""
            
            result = await self._agent.run(prompt)
            response_text = result.data
            
            # Parse response
            summary = ""
            keywords = []
            
            if "SUMMARY:" in response_text and "KEYWORDS:" in response_text:
                parts = response_text.split("KEYWORDS:")
                summary = parts[0].replace("SUMMARY:", "").strip()
                keywords_str = parts[1].strip()
                keywords = [k.strip() for k in keywords_str.split(",")]
            
            return summary, keywords
            
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            return "Summary generation failed.", []
    
    async def run(self, document: Document, file_path: str, **kwargs) -> ProcessingResult:
        """Main entry point."""
        return await self.process_document(document, file_path, **kwargs)
