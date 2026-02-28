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
        student_name: Optional[str] = None,
    ) -> GradingResult:
        """
        Grade a student assignment.

        Args:
            assignment: Assignment entity
            rubric: List of grading criteria
            submission_file_path: Path to submission file (optional, for images)
            student_name: Student's display name (for personalized feedback)

        Returns:
            Grading result with score and feedback
        """
        try:
            logger.info(f"Grading assignment {assignment.id}")

            # Extract submission content
            submission_text = None
            image_data = None  # For direct vision grading

            if submission_file_path:
                # Try OCR first, fall back to vision API if tesseract unavailable
                try:
                    submission_text = self.parser.parse_file(
                        submission_file_path, use_ocr=True
                    )
                    assignment.submission_text = submission_text
                except Exception as ocr_err:
                    logger.warning(
                        f"OCR failed ({ocr_err}), falling back to "
                        f"Gemini vision for {submission_file_path}"
                    )
                    # Read image bytes for direct vision grading
                    import mimetypes

                    with open(submission_file_path, "rb") as f:
                        image_data = f.read()
                    mime_type = (
                        mimetypes.guess_type(submission_file_path)[0]
                        or "image/jpeg"
                    )
            elif assignment.submission_text:
                submission_text = assignment.submission_text
            else:
                return GradingResult(
                    total_score=0.0,
                    feedback="Không thể đánh giá: Không có bài làm để chấm.",
                )

            # Build rubric description
            rubric_desc = self._format_rubric(rubric)

            # Create grading prompt
            if image_data:
                # Vision mode: send image directly to Gemini
                from pydantic_ai import BinaryContent

                # Derive first name for personalized feedback
                first_name = (student_name or "").split()[-1] if student_name else "Học sinh"

                prompt_text = f"""Look at this student's homework image and grade it based on the rubric.

Student Name: {student_name or 'Học sinh'}
Assignment Title: {assignment.title}
Subject: {assignment.subject}
Maximum Score: {assignment.max_score}

RUBRIC:
{rubric_desc}

IMPORTANT RULES:
- Do NOT use any markdown formatting (no *, **, #, etc.)
- Write all feedback in plain Vietnamese text only
- The TOTAL_SCORE must be a number, grade fairly based on what you see
- The FEEDBACK must be a single short sentence (max 100 characters) starting with "{first_name}" (the student's first name), written like a teacher's objective comment about the student's work, for example: "{first_name} da thuc hien dung cac phep tinh co ban, nhung can can than hon voi phan rut gon phan so."

Please read the student's handwritten work from the image and grade it.

You MUST format your response EXACTLY as follows (keep section headers in UPPERCASE):

TOTAL_SCORE: [number out of {assignment.max_score}]

FEEDBACK:
[one short sentence in Vietnamese starting with "{first_name}", max 100 chars, no special characters]

STRENGTHS:
- [strength 1]
- [strength 2]

IMPROVEMENTS:
- [improvement 1]
- [improvement 2]"""

                result = await self._agent.run(
                    [
                        BinaryContent(
                            data=image_data, media_type=mime_type
                        ),
                        prompt_text,
                    ]
                )
            else:
                # Text mode: submission already extracted
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
                feedback=f"Lỗi khi chấm bài: {str(e)}.\nVui lòng liên hệ giáo viên.",
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

            # Fallback: scan entire response for TOTAL_SCORE pattern
            if total_score == 0.0:
                import re
                score_match = re.search(
                    r'TOTAL_SCORE[:\s]+([\d.]+)', response, re.IGNORECASE
                )
                if score_match:
                    try:
                        total_score = float(score_match.group(1))
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

            # Strip markdown artifacts from all text fields
            feedback = feedback.replace('*', '').replace('#', '').strip()
            strengths = [s.replace('*', '').strip() for s in strengths]
            improvements = [i.replace('*', '').strip() for i in improvements]

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
