"""
Repository for storing and retrieving student profiles via Milvus.

Student profiles are used by the ``/hw`` command to generate personalised
supplementary homework suggestions based on each student's strengths,
weaknesses, subjects, and learning level.
"""

from typing import Optional

from database.milvus_client import milvus_client
from utils.embeddings import generate_single_embedding
from utils.logger import logger

# Collection name (prefixed by settings.milvus_collection_prefix)
STUDENT_PROFILES_COLLECTION = "student_profiles"


def _build_profile_text(
    student_name: str,
    grade: int,
    class_name: str,
    subjects: list[str],
    strengths: list[str],
    weaknesses: list[str],
    learning_level: str = "",
    notes: str = "",
) -> str:
    """
    Build a plain-text summary of the student profile for embedding.

    The text is written so that semantic search on queries like
    "hồ sơ học sinh" or "điểm yếu môn Toán" produces high cosine
    similarity with relevant profiles.
    """
    parts = [
        f"Hồ sơ học sinh: {student_name}.",
        f"Lớp: {class_name}, Khối: {grade}.",
    ]
    if subjects:
        parts.append(f"Các môn học: {', '.join(subjects)}.")
    if learning_level:
        parts.append(f"Trình độ: {learning_level}.")
    if strengths:
        parts.append(f"Điểm mạnh: {', '.join(strengths)}.")
    if weaknesses:
        parts.append(f"Điểm yếu, cần cải thiện: {', '.join(weaknesses)}.")
    if notes:
        parts.append(f"Ghi chú: {notes}")
    return " ".join(parts)


async def store_student_profile(
    student_id: str,
    student_name: str,
    grade: int,
    class_name: str,
    subjects: list[str] | None = None,
    strengths: list[str] | None = None,
    weaknesses: list[str] | None = None,
    learning_level: str = "",
    notes: str = "",
) -> bool:
    """
    Embed and store (upsert) a student profile in Milvus.

    Returns True on success, False if Milvus is unavailable or embedding
    fails.
    """
    try:
        text = _build_profile_text(
            student_name=student_name,
            grade=grade,
            class_name=class_name,
            subjects=subjects or [],
            strengths=strengths or [],
            weaknesses=weaknesses or [],
            learning_level=learning_level,
            notes=notes,
        )

        embedding = await generate_single_embedding(text)

        metadata = {
            "subjects": subjects or [],
            "strengths": strengths or [],
            "weaknesses": weaknesses or [],
            "learning_level": learning_level,
            "notes": notes,
        }

        milvus_client.insert_student_profile(
            collection_name=STUDENT_PROFILES_COLLECTION,
            student_id=student_id,
            student_name=student_name,
            grade=grade,
            class_name=class_name,
            text=text,
            embedding=embedding,
            metadata=metadata,
        )
        return True

    except Exception as e:
        logger.warning(f"[STUDENT_PROFILE_REPO] Failed to store profile: {e}")
        return False


async def get_student_profile(student_id: str) -> Optional[dict]:
    """
    Retrieve a student profile by exact ``student_id``.

    Returns the profile dict or ``None`` if not found.
    """
    try:
        # We need a dummy embedding for the search call (Milvus requires it).
        # Use a short query that will match any profile.
        query_embedding = await generate_single_embedding("hồ sơ học sinh")

        results = milvus_client.search_student_profiles(
            collection_name=STUDENT_PROFILES_COLLECTION,
            query_embedding=query_embedding,
            student_id=student_id,
            top_k=1,
        )

        if results:
            return results[0]
        return None

    except Exception as e:
        logger.warning(f"[STUDENT_PROFILE_REPO] Failed to get profile: {e}")
        return None


async def search_student_profiles(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Search student profiles by semantic similarity.

    Args:
        query: Natural-language search text.
        top_k: Maximum results.

    Returns:
        List of profile dicts (empty if Milvus is unavailable).
    """
    try:
        query_embedding = await generate_single_embedding(query)
        return milvus_client.search_student_profiles(
            collection_name=STUDENT_PROFILES_COLLECTION,
            query_embedding=query_embedding,
            top_k=top_k,
        )
    except Exception as e:
        logger.warning(f"[STUDENT_PROFILE_REPO] Failed to search profiles: {e}")
        return []
