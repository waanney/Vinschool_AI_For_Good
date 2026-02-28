"""
In-memory submission store for graded student work.

Stores graded homework submissions from the /grade Google Chat command.
Each submission records the student info, grading results, and attachment
paths so the LMS teacher dashboard can display them.

This is a temporary in-memory store (module-level list) for the demo.
When PostgreSQL is wired up, migrate to a proper repository.
"""

import uuid
from datetime import datetime
from typing import Optional

from utils.logger import logger


# Module-level in-memory store (same pattern as zalo_message_store)
submission_store: list[dict] = []


def add_submission(
    student_id: str,
    student_name: str,
    score: float,
    max_score: float,
    feedback: str,
    attachment_paths: list[str],
    subject: str = "Mathematics",
    assignment_title: str = "Homework Submission",
    details: Optional[dict] = None,
) -> dict:
    """
    Add a graded submission to the store.

    Args:
        student_id: Google Chat user ID of the student.
        student_name: Display name of the student.
        score: AI-graded score.
        max_score: Maximum possible score.
        feedback: AI-generated feedback text.
        attachment_paths: List of file paths for submitted images.
        subject: Subject name (default: Mathematics).
        assignment_title: Title of the assignment.
        details: Optional dict with criteria_scores, strengths, improvements.

    Returns:
        The newly created submission dict.
    """
    submission = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "student_name": student_name,
        "assignment_title": assignment_title,
        "subject": subject,
        "score": score,
        "max_score": max_score,
        "feedback": feedback,
        "attachment_paths": attachment_paths,
        "details": details or {},
        "graded_at": datetime.utcnow().isoformat(),
        "is_viewed": False,
    }

    submission_store.append(submission)

    logger.info(
        f"[SUBMISSION] Stored submission {submission['id']} "
        f"for {student_name}: {score}/{max_score}"
    )

    return submission


def get_submissions() -> list[dict]:
    """Return all submissions, sorted by graded_at descending (newest first)."""
    return sorted(
        submission_store,
        key=lambda s: s["graded_at"],
        reverse=True,
    )


def get_unviewed_count() -> int:
    """Return the number of unviewed submissions."""
    return sum(1 for s in submission_store if not s["is_viewed"])


def mark_viewed(submission_id: str) -> bool:
    """
    Mark a submission as viewed by the teacher.

    Args:
        submission_id: ID of the submission to mark.

    Returns:
        True if found and marked, False if not found.
    """
    for submission in submission_store:
        if submission["id"] == submission_id:
            submission["is_viewed"] = True
            logger.info(f"[SUBMISSION] Marked {submission_id} as viewed")
            return True

    logger.warning(f"[SUBMISSION] Submission {submission_id} not found")
    return False


def clear_submissions() -> None:
    """Clear all submissions (for testing)."""
    submission_store.clear()
    logger.info("[SUBMISSION] Store cleared")
