"""
Repository for storing and retrieving daily lesson content via Milvus.

Teachers upload lesson material (per subject, per day).  The content is
embedded and stored in the ``daily_lessons`` collection so that:

* ``/dailysum`` can retrieve all lessons for a given date and summarise
  them.
* ``/ask`` can include the latest lesson context in the AI prompt.
* ``load_lesson_context()`` can pull from Milvus instead of a static
  ``data/lesson.txt`` file.
"""

from typing import Optional

from database.milvus_client import milvus_client
from utils.embeddings import generate_single_embedding
from utils.logger import logger

# Collection name (prefixed by settings.milvus_collection_prefix)
DAILY_LESSONS_COLLECTION = "daily_lessons"


async def store_daily_lesson(
    date: str,
    subject: str,
    title: str,
    content: str,
    homework: str = "",
    notes: str = "",
) -> bool:
    """
    Embed and store a single daily lesson entry in Milvus.

    Args:
        date: Lesson date in ``YYYY-MM-DD`` format.
        subject: Subject name (e.g. "Toán", "Khoa học").
        title: Lesson title / topic.
        content: Full lesson text (knowledge points, examples, etc.).
        homework: Homework description (optional).
        notes: Additional notes such as deadlines (optional).

    Returns:
        True on success, False if Milvus is unavailable or embedding fails.
    """
    try:
        # Build a text block that captures the full lesson for embedding
        parts = [
            f"Bài học ngày {date}. Môn: {subject}. Chủ đề: {title}.",
            content,
        ]
        if homework:
            parts.append(f"Bài tập về nhà: {homework}")
        if notes:
            parts.append(f"Ghi chú: {notes}")
        text = "\n".join(parts)

        embedding = await generate_single_embedding(text)

        metadata = {
            "homework": homework,
            "notes": notes,
        }

        milvus_client.insert_daily_lesson(
            collection_name=DAILY_LESSONS_COLLECTION,
            date=date,
            subject=subject,
            title=title,
            text=text,
            embedding=embedding,
            metadata=metadata,
        )
        return True

    except Exception as e:
        logger.warning(f"[DAILY_LESSON_REPO] Failed to store lesson: {e}")
        return False


async def get_lessons_by_date(date: str) -> list[dict]:
    """
    Retrieve all lessons for a specific date.

    Performs a broad semantic search filtered to the given date and
    returns up to 10 lesson entries (enough for a full school day).
    """
    try:
        query_embedding = await generate_single_embedding(
            f"bài học ngày {date}"
        )
        return milvus_client.search_daily_lessons(
            collection_name=DAILY_LESSONS_COLLECTION,
            query_embedding=query_embedding,
            date=date,
            top_k=10,
        )
    except Exception as e:
        logger.warning(f"[DAILY_LESSON_REPO] Failed to get lessons for {date}: {e}")
        return []


async def search_lessons(
    query: str,
    date: str | None = None,
    subject: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Semantic search across daily lessons.

    Args:
        query: Natural-language search text.
        date: Optional date filter (``YYYY-MM-DD``).
        subject: Optional subject filter.
        top_k: Maximum results.

    Returns:
        List of lesson dicts (empty if Milvus is unavailable).
    """
    try:
        query_embedding = await generate_single_embedding(query)
        return milvus_client.search_daily_lessons(
            collection_name=DAILY_LESSONS_COLLECTION,
            query_embedding=query_embedding,
            date=date,
            subject=subject,
            top_k=top_k,
        )
    except Exception as e:
        logger.warning(f"[DAILY_LESSON_REPO] Failed to search lessons: {e}")
        return []


def build_lesson_context_from_results(results: list[dict]) -> str:
    """
    Combine search results into a single lesson context string suitable
    for embedding in the LLM system prompt.

    Each lesson is separated by a section divider matching the format
    of ``data/lesson.txt`` so the existing system prompt rules still
    apply.
    """
    if not results:
        return ""

    sections: list[str] = []
    for r in results:
        sections.append(r.get("text", ""))

    return "\n\n".join(sections)
