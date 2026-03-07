"""
Seed the ``daily_lessons`` Milvus collection from ``data/lesson.txt``.

Parses the lesson file into per-subject sections and stores each one
as an individual entry so ``/dailysum`` and ``/ask`` can retrieve them
from the vector database.

Usage (from backend/):
    python -m scripts.seed_daily_lessons
"""

import asyncio
import re
import sys
from datetime import date
from pathlib import Path

# Ensure backend/ is on sys.path when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.repositories.daily_lesson_repository import store_daily_lesson
from utils.logger import logger

LESSON_FILE = Path(__file__).resolve().parent.parent / "data" / "lesson.txt"

# Regex to split the file on "===== SUBJECT — TOPIC (Tuần XX) =====" headers
_SECTION_RE = re.compile(
    r"=====\s*(.+?)\s*=====",
    re.MULTILINE,
)


def _parse_lesson_file(text: str, lesson_date: str) -> list[dict]:
    """
    Split the lesson.txt content into per-subject entries.

    Returns a list of dicts with keys:
        date, subject, title, content, homework, notes
    """
    entries: list[dict] = []

    # Split by ===== headers
    parts = _SECTION_RE.split(text)

    # parts[0] = text before first header (usually empty)
    # parts[1] = first header, parts[2] = body after first header, etc.
    i = 1
    while i < len(parts) - 1:
        header = parts[i].strip()
        body = parts[i + 1].strip()
        i += 2

        # Parse header: "TOÁN - PHÂN SỐ (Tuần 12)" or "LỊCH HỌC TUẦN 12"
        subject = header.split("-")[0].strip().split("(")[0].strip()
        title = header

        # Try to extract homework from body
        homework = ""
        notes = ""
        hw_match = re.search(r"Bài tập.*?:(.*?)(?=\n=====|\n\n[A-Z]|\Z)", body, re.DOTALL)
        if hw_match:
            homework = hw_match.group(1).strip()

        notes_match = re.search(r"Ghi chú:(.*?)(?=\n=====|\Z)", body, re.DOTALL)
        if notes_match:
            notes = notes_match.group(1).strip()

        entries.append({
            "date": lesson_date,
            "subject": subject,
            "title": title,
            "content": body,
            "homework": homework,
            "notes": notes,
        })

    return entries


async def main() -> None:
    """Parse lesson.txt and seed into Milvus."""
    if not LESSON_FILE.exists():
        logger.error(f"Lesson file not found: {LESSON_FILE}")
        return

    text = LESSON_FILE.read_text(encoding="utf-8").strip()
    if not text:
        logger.error("Lesson file is empty")
        return

    # Use today's date as the lesson date
    lesson_date = date.today().isoformat()

    entries = _parse_lesson_file(text, lesson_date)
    logger.info(
        f"Parsed {len(entries)} lesson sections from {LESSON_FILE.name} "
        f"(date={lesson_date})"
    )

    success_count = 0
    for entry in entries:
        ok = await store_daily_lesson(
            date=entry["date"],
            subject=entry["subject"],
            title=entry["title"],
            content=entry["content"],
            homework=entry["homework"],
            notes=entry["notes"],
        )
        if ok:
            success_count += 1
            logger.info(f"  ✓ {entry['subject']} — {entry['title']}")
        else:
            logger.warning(f"  ✗ Failed: {entry['subject']} — {entry['title']}")

    logger.info(f"Done — {success_count}/{len(entries)} lessons stored.")


if __name__ == "__main__":
    asyncio.run(main())
