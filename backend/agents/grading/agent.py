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
    feedback: str  # concise for GChat reply & LMS table
    detailed_feedback: str = ""  # full paragraph for email & LMS detail
    criteria_scores: Dict[str, float] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)


class GradingAgent(BaseAgent):
    """
    Grading Agent for automated homework assessment.

    Capabilities:
    - Grade homework against rubric
    - Extract text from images (OCR primary, Gemini vision fallback)
    - Provide detailed feedback
    - Suggest improvements
    """

    SYSTEM_PROMPT = """You are Cô Hana, a caring and experienced primary-school teacher at Vinschool.
You always refer to yourself as "Cô Hana" (never "co/thay", "thay", or any other title).
Your role is to:
1. Evaluate student work fairly and accurately
2. Provide constructive, encouraging feedback in the warm voice of Cô Hana
3. Identify strengths and areas for improvement
4. Grade based on provided rubric criteria

Grading principles:
- Be consistent and objective
- Focus on learning outcomes
- Provide specific, actionable feedback
- Encourage student growth
- Always write feedback in proper Vietnamese with full diacritical marks (e.g. "nắm khá chắc" not "nam kha chac")
- Address the student by their short name (last two words of their full name)
- Preserve the student's name exactly as given — do NOT add diacritical marks to a name provided without them
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

                # Derive short name (last two words) for personalized feedback.
                # Vietnamese names: family-middle-given, e.g. "Nguyen Van An" → "Van An"
                name_parts = (student_name or "").split()
                short_name = " ".join(name_parts[-2:]) if len(name_parts) >= 2 else (name_parts[0] if name_parts else "Hoc sinh")

                prompt_text = f"""Look at this student's homework image and grade it based on the rubric.

Student Name: {student_name or 'Hoc sinh'}
Short Name (use this when addressing the student): {short_name}
Assignment Title: {assignment.title}
Subject: {assignment.subject}
Maximum Score: {assignment.max_score}

RUBRIC:
{rubric_desc}

GRADING METHOD:
1. First, identify every question and sub-question in the image.
2. For each one, determine whether the student's answer is CORRECT or INCORRECT.
3. Count: total questions, correct answers, incorrect answers.
4. Compute TOTAL_SCORE = (correct / total) * {assignment.max_score}, rounded to one decimal.
5. Do NOT deduct points for handwriting quality, neatness, or missing working-out.
6. Only deduct points when the final answer is wrong.

IMPORTANT RULES:
- Do NOT use any markdown formatting (no *, **, #, etc.)
- Write all text in proper Vietnamese with full diacritical marks
- The TOTAL_SCORE must be computed from correct/total as described above
- FEEDBACK: one concise sentence (max 100 chars) starting with "{short_name}", summarising how the student did. Include the count like "đúng X/Y câu". Write in proper Vietnamese with diacritical marks.
- DETAILED_FEEDBACK: a paragraph (4-6 sentences) as Cô Hana speaking to the student. Write in proper Vietnamese with diacritical marks. Start with "Chào {short_name}" and sign off naturally. List which specific questions are correct and which are incorrect. Do NOT invent information not visible in the image. Do NOT use "cô/thầy" — always say "Cô Hana".
- Preserve the student's name exactly as given (keep or omit diacritical marks as provided; do NOT add diacritical marks to a name that was given without them).

Please read the student's handwritten work from the image and grade it.

You MUST format your response EXACTLY as follows (keep section headers in UPPERCASE):

TOTAL_SCORE: [number out of {assignment.max_score}]

FEEDBACK:
[one short sentence in proper Vietnamese with diacritical marks, starting with "{short_name}", include correct/total count, max 100 chars]

DETAILED_FEEDBACK:
[paragraph from Cô Hana to the student, 4-6 sentences, proper Vietnamese with diacritical marks]

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
                name_parts = (student_name or "").split()
                short_name = " ".join(name_parts[-2:]) if len(name_parts) >= 2 else (name_parts[0] if name_parts else "Hoc sinh")

                prompt = f"""Grade this student assignment based on the provided rubric.

Student Name: {student_name or 'Hoc sinh'}
Short Name: {short_name}
Assignment Title: {assignment.title}
Subject: {assignment.subject}
Maximum Score: {assignment.max_score}

RUBRIC:
{rubric_desc}

STUDENT SUBMISSION:
{submission_text}

GRADING METHOD:
1. Identify every question and sub-question in the submission.
2. For each one, determine whether the student's answer is CORRECT or INCORRECT.
3. Count: total questions, correct answers, incorrect answers.
4. Compute TOTAL_SCORE = (correct / total) * {assignment.max_score}, rounded to one decimal.
5. Do NOT deduct points for presentation, neatness, or missing working-out.
6. Only deduct points when the final answer is wrong.

IMPORTANT RULES:
- Do NOT use any markdown formatting (no *, **, #, etc.)
- Write all text in proper Vietnamese with full diacritical marks
- FEEDBACK: one concise sentence (max 100 chars) starting with "{short_name}". Include the count like "đúng X/Y câu". Write in proper Vietnamese with diacritical marks.
- DETAILED_FEEDBACK: a paragraph (4-6 sentences) as Cô Hana speaking to the student. Write in proper Vietnamese with diacritical marks.
- Preserve the student's name exactly as given (do NOT add diacritical marks to a name given without them)

Format your response as:
CRITERION_SCORES:
[criterion_name]: [score] / [max_points]
...

TOTAL_SCORE: [score]

FEEDBACK:
[one short sentence in proper Vietnamese with diacritical marks, starting with "{short_name}", include correct/total count, max 100 chars]

DETAILED_FEEDBACK:
[paragraph from Cô Hana, 4-6 sentences, proper Vietnamese with diacritical marks]

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

            # Extract feedback (concise) and detailed feedback (full paragraph)
            feedback = sections.get('FEEDBACK', '').strip()
            detailed_feedback = sections.get('DETAILED_FEEDBACK', '').strip()

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
            detailed_feedback = detailed_feedback.replace('*', '').replace('#', '').strip()
            strengths = [s.replace('*', '').strip() for s in strengths]
            improvements = [i.replace('*', '').strip() for i in improvements]

            return GradingResult(
                total_score=min(total_score, max_score),  # Cap at max
                feedback=feedback,
                detailed_feedback=detailed_feedback,
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
