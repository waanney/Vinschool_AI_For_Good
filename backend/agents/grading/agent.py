"""
Grading Agent.
Handles automated homework grading with rubric-based evaluation.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from agents.base.agent import BaseAgent, AgentConfig
from domain.models.assignment import Assignment
from utils.document_parser import DocumentParser
from utils.logger import logger


class GradingCriteria(BaseModel):
    """Grading criteria/rubric."""
    criteria_name: str
    max_points: float
    description: str


class GradingResult(BaseModel):
    """Result of grading an assignment."""
    total_score: float
    feedback: str
    criteria_scores: Dict[str, float] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)


class GradingAgent(BaseAgent):
    """
    Grading Agent for automated homework assessment.
    
    Capabilities:
    - Grade homework against rubric
    - Extract text from images (OCR for handwritten work)
    - Provide detailed feedback
    - Suggest improvements
    """
    
    SYSTEM_PROMPT = """You are an expert educational assessment assistant.
Your role is to:
1. Evaluate student work fairly and accurately
2. Provide constructive, encouraging feedback
3. Identify strengths and areas for improvement
4. Grade based on provided rubric criteria

Grading principles:
- Be consistent and objective
- Focus on learning outcomes
- Provide specific, actionable feedback
- Encourage student growth
- Use Vietnamese language for feedback when appropriate
"""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        # Use specific model for grading if configured
        from config import settings
        if config is None:
            config = AgentConfig()
            # Use grading model from settings (respects provider choice)
            config.model_name = settings.grading_llm_model
        
        super().__init__(config)
        self.parser = DocumentParser()
        self._agent = self._create_agent(system_prompt=self.SYSTEM_PROMPT)
    
    async def grade_assignment(
        self,
        assignment: Assignment,
        rubric: List[GradingCriteria],
        submission_file_path: Optional[str] = None,
    ) -> GradingResult:
        """
        Grade a student assignment.
        
        Args:
            assignment: Assignment entity
            rubric: List of grading criteria
            submission_file_path: Path to submission file (optional, for images)
            
        Returns:
            Grading result with score and feedback
        """
        try:
            logger.info(f"Grading assignment {assignment.id}")
            
            # Extract submission content
            if submission_file_path:
                # Extract text from image using OCR
                submission_text = self.parser.parse_file(submission_file_path, use_ocr=True)
                assignment.submission_text = submission_text
            elif assignment.submission_text:
                submission_text = assignment.submission_text
            else:
                return GradingResult(
                    total_score=0.0,
                    feedback="Không thểđánh giá: Không có bài làm để chấm.",
                )
            
            # Build rubric description
            rubric_desc = self._format_rubric(rubric)
            
            # Create grading prompt
            prompt = f"""Grade this student assignment based on the provided rubric.

Assignment Title: {assignment.title}
Subject: {assignment.subject}
Maximum Score: {assignment.max_score}

RUBRIC:
{rubric_desc}

STUDENT SUBMISSION:
{submission_text}

Please provide:
1. Score for each criterion
2. Total score (out of {assignment.max_score})
3. Detailed feedback in Vietnamese
4. List of 2-3 strengths
5. List of 2-3 areas for improvement

Format your response as:
CRITERION_SCORES:
[criterion_name]: [score] / [max_points]
...

TOTAL_SCORE: [score]

FEEDBACK:
[detailed feedback in Vietnamese]

STRENGTHS:
- [strength 1]
- [strength 2]

IMPROVEMENTS:
- [improvement 1]
- [improvement 2]"""
            
            # Run grading agent
            result = await self._agent.run(prompt)
            response = str(result.output)
            
            # Parse response
            grading_result = self._parse_grading_response(response, rubric, assignment.max_score)
            
            logger.info(f"Graded assignment {assignment.id}: Score {grading_result.total_score}/{assignment.max_score}")
            
            return grading_result
            
        except Exception as e:
            logger.error(f"Error grading assignment {assignment.id}: {e}")
            return GradingResult(
                total_score=0.0,
                feedback=f"Lỗi khi chấm bài: {str(e)}. Vui lòng liên hệ giáo viên.",
            )
    
    def _format_rubric(self, rubric: List[GradingCriteria]) -> str:
        """Format rubric for prompt."""
        lines = []
        for i, criteria in enumerate(rubric, 1):
            lines.append(
                f"{i}. {criteria.criteria_name} ({criteria.max_points} points)\n"
                f"   Description: {criteria.description}"
            )
        return "\n\n".join(lines)
    
    def _parse_grading_response(
        self,
        response: str,
        rubric: List[GradingCriteria],
        max_score: float,
    ) -> GradingResult:
        """Parse structured grading response."""
        try:
            # Extract sections
            sections = {}
            current_section = None
            current_content = []
            
            for line in response.split('\n'):
                line = line.strip()
                if line.endswith(':') and line.isupper():
                    if current_section:
                        sections[current_section] = '\n'.join(current_content)
                    current_section = line[:-1]
                    current_content = []
                else:
                    current_content.append(line)
            
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            
            # Parse total score
            total_score = 0.0
            if 'TOTAL_SCORE' in sections:
                try:
                    total_score = float(sections['TOTAL_SCORE'].split()[0])
                except:
                    pass
            
            # Parse criterion scores
            criteria_scores = {}
            if 'CRITERION_SCORES' in sections:
                for line in sections['CRITERION_SCORES'].split('\n'):
                    if ':' in line:
                        parts = line.split(':')
                        name = parts[0].strip()
                        try:
                            score = float(parts[1].split('/')[0].strip())
                            criteria_scores[name] = score
                        except:
                            pass
            
            # Extract feedback
            feedback = sections.get('FEEDBACK', '').strip()
            
            # Extract strengths
            strengths = []
            if 'STRENGTHS' in sections:
                strengths = [
                    line.strip('- ').strip()
                    for line in sections['STRENGTHS'].split('\n')
                    if line.strip().startswith('-')
                ]
            
            # Extract improvements
            improvements = []
            if 'IMPROVEMENTS' in sections:
                improvements = [
                    line.strip('- ').strip()
                    for line in sections['IMPROVEMENTS'].split('\n')
                    if line.strip().startswith('-')
                ]
            
            return GradingResult(
                total_score=min(total_score, max_score),  # Cap at max
                feedback=feedback,
                criteria_scores=criteria_scores,
                strengths=strengths,
                improvements=improvements,
            )
            
        except Exception as e:
            logger.error(f"Error parsing grading response: {e}")
            # Fallback: use full response as feedback
            return GradingResult(
                total_score=0.0,
                feedback=response,
            )
    
    async def run(self, assignment: Assignment, rubric: List[GradingCriteria], **kwargs) -> GradingResult:
        """Main entry point."""
        return await self.grade_assignment(assignment, rubric, **kwargs)
