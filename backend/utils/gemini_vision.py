"""
Gemini 2.5 Pro vision utility for parsing lesson images.

Uses the google-generativeai SDK to send an image to Gemini and
extract structured lesson content (subject, title, key points,
homework, etc.) as JSON.
"""

import json
from typing import Optional

import google.generativeai as genai

from config.settings import get_settings
from utils.logger import logger

# Model used for vision parsing — Gemini 2.5 Pro supports images natively.
VISION_MODEL = "gemini-2.5-pro"


def _ensure_configured() -> None:
    """Make sure the genai SDK is configured with the API key."""
    settings = get_settings()
    if settings.gemini_api_key:
        genai.configure(api_key=settings.gemini_api_key)


async def parse_lesson_image(
    image_bytes: bytes,
    mime_type: str,
    date_hint: str = "",
    subject_hint: str = "",
) -> dict:
    """
    Send a lesson image to Gemini 2.5 Pro and extract structured content.

    Args:
        image_bytes: Raw bytes of the uploaded image.
        mime_type: MIME type (e.g. ``image/jpeg``, ``image/png``).
        date_hint: Optional date context (``YYYY-MM-DD``).
        subject_hint: Optional subject hint to guide parsing.

    Returns:
        A dict with keys:
        ``subject``, ``title``, ``content``, ``homework``, ``notes``.
        All values are strings (possibly empty).

    Raises:
        ValueError: If Gemini returns unparseable output.
        RuntimeError: If the API call itself fails.
    """
    _ensure_configured()

    model = genai.GenerativeModel(VISION_MODEL)

    # Build the prompt — instruct Gemini to return valid JSON only.
    date_ctx = f"\nNgày bài học: {date_hint}" if date_hint else ""
    subject_ctx = f"\nMôn học gợi ý: {subject_hint}" if subject_hint else ""

    prompt = f"""Bạn là trợ lý AI trích xuất nội dung bài học từ hình ảnh tài liệu giáo dục tiểu học Việt Nam.

Hãy đọc kỹ hình ảnh đính kèm và trích xuất các thông tin sau:{date_ctx}{subject_ctx}

Trả về **CHỈ** một JSON object hợp lệ (không markdown, không giải thích) theo đúng format:
{{
  "subject": "<tên môn học, ví dụ: Toán, Khoa học, Tiếng Việt>",
  "title": "<tiêu đề / chủ đề bài học>",
  "content": "<toàn bộ nội dung chính của bài học, bao gồm kiến thức, ví dụ, lời giải — giữ nguyên tiếng Việt>",
  "homework": "<bài tập về nhà nếu có, để trống nếu không>",
  "notes": "<ghi chú thêm, deadline, hoặc hướng dẫn — để trống nếu không>"
}}

Lưu ý:
- Giữ nguyên ngôn ngữ gốc (tiếng Việt hoặc tiếng Anh) trong hình.
- Nếu hình có nhiều phần (lesson plan, bài tập, tài liệu thêm), gộp vào trường "content".
- Nếu không xác định được môn học, hãy suy luận từ nội dung.
- Trả về JSON thuần, KHÔNG bọc trong ```json``` hay bất kỳ markdown nào."""

    try:
        response = model.generate_content(
            [
                {"mime_type": mime_type, "data": image_bytes},
                prompt,
            ],
        )

        raw_text = response.text.strip()

        # Strip markdown fences if Gemini added them despite instructions
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1]
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]
        raw_text = raw_text.strip()

        parsed: dict = json.loads(raw_text)

        # Normalise keys — ensure all expected keys exist
        result = {
            "subject": str(parsed.get("subject", subject_hint or "")),
            "title": str(parsed.get("title", "")),
            "content": str(parsed.get("content", "")),
            "homework": str(parsed.get("homework", "")),
            "notes": str(parsed.get("notes", "")),
        }

        logger.info(
            f"[GEMINI_VISION] Parsed lesson image: "
            f"subject={result['subject']}, title={result['title'][:60]}"
        )
        return result

    except json.JSONDecodeError as exc:
        logger.error(f"[GEMINI_VISION] JSON parse error: {exc}\nRaw: {raw_text[:500]}")
        raise ValueError(f"Gemini returned invalid JSON: {exc}") from exc
    except Exception as exc:
        logger.error(f"[GEMINI_VISION] API error: {exc}")
        raise RuntimeError(f"Gemini vision API failed: {exc}") from exc
