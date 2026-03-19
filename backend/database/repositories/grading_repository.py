"""
Repository for storing and retrieving grading results via Milvus.

When a student's homework is graded (``/grade``), the result is embedded
and persisted here.  When a student later asks about their score
(``/ask``), ``ChatService`` queries this repository to inject grading
context into the AI prompt so Cô Hana can answer accurately.
"""

from typing import Optional

from database.milvus_client import milvus_client
from utils.embeddings import generate_single_embedding
from utils.logger import logger

# Collection name (prefixed by settings.milvus_collection_prefix)
GRADING_COLLECTION = "grading_results"


def _build_grading_text(
    student_name: str,
    subject: str,
    assignment_title: str,
    score: float,
    max_score: float,
    feedback: str,
    detailed_feedback: str,
) -> str:
    """
    Build a plain-text summary of the grading result for embedding.

    The text is written so that semantic search on student questions
    like "điểm của con bao nhiêu?" or "con làm sai chỗ nào?" will
    produce high cosine similarity.
    """
    parts = [
        f"Kết quả chấm bài của {student_name}.",
        f"Môn: {subject}. Bài: {assignment_title}.",
        f"Điểm: {score}/{max_score}.",
    ]
    if feedback:
        parts.append(f"Nhận xét ngắn: {feedback}")
    if detailed_feedback:
        parts.append(f"Nhận xét chi tiết: {detailed_feedback}")
    return " ".join(parts)


async def store_grading_result(
    student_id: str,
    student_name: str,
    subject: str,
    assignment_title: str,
    score: float,
    max_score: float,
    feedback: str,
    detailed_feedback: str = "",
    graded_at: str = "",
) -> bool:
    """
    Embed and store a grading result in Milvus.

    Returns True on success, False if Milvus is unavailable or embedding
    fails (the caller should log and continue — this is non-critical).
    """
    try:
        text = _build_grading_text(
            student_name=student_name,
            subject=subject,
            assignment_title=assignment_title,
            score=score,
            max_score=max_score,
            feedback=feedback,
            detailed_feedback=detailed_feedback,
        )

        embedding = await generate_single_embedding(text)

        metadata = {
            "assignment_title": assignment_title,
            "feedback": feedback,
            "detailed_feedback": detailed_feedback,
            "graded_at": graded_at,
        }

        milvus_client.insert_grading_result(
            collection_name=GRADING_COLLECTION,
            student_id=student_id,
            student_name=student_name,
            subject=subject,
            score=score,
            max_score=max_score,
            text=text,
            embedding=embedding,
            metadata=metadata,
        )
        return True

    except Exception as e:
        logger.warning(f"[GRADING_REPO] Failed to store grading result in Milvus: {e}")
        return False


async def search_student_grades(
    query: str,
    student_id: str | None = None,
    top_k: int = 3,
) -> list[dict]:
    """
    Search grading results relevant to a student question.

    Args:
        query: The student's natural-language question.
        student_id: If provided, restrict results to this student.
        top_k: Maximum results.

    Returns:
        List of grading result dicts (empty if Milvus is unavailable).
    """
    try:
        query_embedding = await generate_single_embedding(query)
        return milvus_client.search_grading_results(
            collection_name=GRADING_COLLECTION,
            query_embedding=query_embedding,
            student_id=student_id,
            top_k=top_k,
        )
    except Exception as e:
        logger.warning(f"[GRADING_REPO] Failed to search grading results: {e}")
        return []
