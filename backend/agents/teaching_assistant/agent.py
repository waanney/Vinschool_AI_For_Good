"""
Teaching Assistant Agent using PydanticAI.
Main agent for educational support tasks.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from agents.base.agent import BaseAgent, AgentConfig
from database.repositories.document_repository import DocumentRepository
from utils.embeddings import generate_single_embedding
from utils.logger import logger


class QuestionContext(BaseModel):
    """Context for question answering."""
    question: str
    student_id: str
    grade: int
    subject: str
    class_name: Optional[str] = None


class AnswerResponse(BaseModel):
    """Response from question answering."""
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)
    escalate_to_teacher: bool = False
    reasoning: str = ""


class SummaryRequest(BaseModel):
    """Request for content summarization."""
    content: str
    target_audience: str = "students"  # students, parents, teachers
    max_length: int = 500


class TeachingAssistantAgent(BaseAgent):
    """
    Teaching Assistant Agent.
    
    Capabilities:
    - Answer student questions using RAG
    - Summarize daily content
    - Generate personalized exercises
    - Provide feedback and recommendations
    """
    
    SYSTEM_PROMPT = """You are an intelligent teaching assistant for Vinschool.
Your role is to help students learn effectively by:
1. Answering questions clearly and accurately using provided context
2. Explaining concepts in an age-appropriate manner
3. Providing examples and practice problems
4. Encouraging critical thinking

When answering questions:
- Use the provided context from course materials
- If uncertain or context is insufficient, recommend escalating to the teacher
- Be supportive and encouraging
- Use Vietnamese language when appropriate
- Cite your sources when possible

Always prioritize student understanding and learning outcomes."""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        super().__init__(config)
        self.document_repo = DocumentRepository()
        self._agent = self._create_agent(
            system_prompt=self.SYSTEM_PROMPT,
            retries=2,
        )
    
    async def answer_question(self, context: QuestionContext) -> AnswerResponse:
        """
        Answer a student question using RAG (Retrieval Augmented Generation).
        
        Args:
            context: Question context with student info
            
        Returns:
            Answer response with confidence and escalation flag
        """
        try:
            # Generate embedding for question
            question_embedding = await generate_single_embedding(context.question)
            
            # Search knowledge base
            search_results = await self.document_repo.semantic_search(
                query_embedding=question_embedding,
                top_k=5,
                grade=context.grade,
                subject=context.subject,
                class_name=context.class_name,
            )
            
            # Prepare context from search results
            if not search_results:
                logger.warning(f"No relevant context found for question: {context.question[:100]}")
                return AnswerResponse(
                    answer="Xin lỗi, tôi không tìm thấy thông tin liên quan trong tài liệu học tập. Hãy hỏi giáo viên nhé!",
                    confidence=0.0,
                    escalate_to_teacher=True,
                    reasoning="No relevant documents found in knowledge base",
                )
            
            # Build context string
            context_texts = []
            sources = []
            for i, result in enumerate(search_results, 1):
                context_texts.append(f"[Context {i}]: {result['text']}")
                sources.append(result['metadata'].get('title', 'Unknown'))
            
            context_str = "\n\n".join(context_texts)
            
            # Calculate confidence based on search scores
            avg_score = sum(r['score'] for r in search_results) / len(search_results)
            
            # Build prompt
            prompt = f"""Question from student (Grade {context.grade}, Subject: {context.subject}):
{context.question}

Relevant context from course materials:
{context_str}

Please provide a clear, helpful answer based on the context above. If the context doesn't contain enough information to answer confidently, say so."""
            
            # Run agent
            result = await self._agent.run(prompt)
            
            # Determine if escalation needed
            escalate = avg_score < 0.6  # Low relevance scores
            reasoning = f"Average relevance score: {avg_score:.2f}"
            
            return AnswerResponse(
                answer=str(result.output),
                confidence=avg_score,
                sources=list(set(sources)),
                escalate_to_teacher=escalate,
                reasoning=reasoning,
            )
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return AnswerResponse(
                answer="Xin lỗi, đã có lỗi xảy ra. Vui lòng hỏi lại sau hoặc liên hệ giáo viên.",
                confidence=0.0,
                escalate_to_teacher=True,
                reasoning=f"Error: {str(e)}",
            )
    
    async def summarize_content(self, request: SummaryRequest) -> str:
        """
        Generate summary of educational content.
        
        Args:
            request: Summary request with content and parameters
            
        Returns:
            Generated summary
        """
        try:
            prompt = f"""Summarize the following educational content for {request.target_audience}.
Keep the summary under {request.max_length} characters.
Focus on key concepts and actionable information.

Content:
{request.content}

Provide a clear, structured summary in Vietnamese."""
            
            result = await self._agent.run(prompt)
            
            logger.info(f"Generated summary for {request.target_audience}")
            
            return str(result.output)
            
        except Exception as e:
            logger.error(f"Error summarizing content: {e}")
            return "Không thể tạo tóm tắt. Vui lòng thử lại sau."
    
    async def generate_personalized_exercises(
        self,
        student_level: str,
        subject: str,
        topic: str,
        num_exercises: int = 5,
    ) -> List[str]:
        """
        Generate personalized practice exercises.
        
        Args:
            student_level: Student's learning level (beginner, intermediate, advanced)
            subject: Subject area
            topic: Specific topic
            num_exercises: Number of exercises to generate
            
        Returns:
            List of generated exercises
        """
        try:
            prompt = f"""Generate {num_exercises} practice exercises for a {student_level} level student.
Subject: {subject}
Topic: {topic}

Requirements:
- Appropriate difficulty for {student_level} level
- Clear and specific problems
- Encourage critical thinking
- Include variety (multiple choice, short answer, problem-solving)
- Use Vietnamese language

Format each exercise clearly numbered."""
            
            result = await self._agent.run(prompt)
            
            # Parse exercises (simple split by numbers)
            exercises_text = str(result.output)
            exercises = [
                ex.strip()
                for ex in exercises_text.split('\n')
                if ex.strip() and any(c.isdigit() for c in ex[:3])
            ]
            
            logger.info(f"Generated {len(exercises)} personalized exercises for {topic}")
            
            return exercises[:num_exercises]
            
        except Exception as e:
            logger.error(f"Error generating exercises: {e}")
            return []
    
    async def run(self, task: str, **kwargs) -> Any:
        """
        Main entry point - routes to appropriate method based on task.
        
        Args:
            task: Task type (answer_question, summarize, generate_exercises)
            **kwargs: Task-specific parameters
            
        Returns:
            Task result
        """
        task_map = {
            "answer_question": self.answer_question,
            "summarize": self.summarize_content,
            "generate_exercises": self.generate_personalized_exercises,
        }
        
        handler = task_map.get(task)
        if handler is None:
            raise ValueError(f"Unknown task: {task}")
        
        return await handler(**kwargs)
