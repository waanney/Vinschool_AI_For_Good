"""
Seed dummy student profiles into Milvus.

Populates the ``student_profiles`` collection with sample class-4B5
students so the ``/hw`` command can be tested immediately.

Usage (from backend/):
    python -m scripts.seed_student_profiles
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend/ is on sys.path when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.repositories.student_profile_repository import store_student_profile
from utils.logger import logger

# Dummy profiles for class 4B5
DUMMY_PROFILES: list[dict] = [
    {
        "student_id": "gchat-users/test-student-001",
        "student_name": "Nguyễn Văn An",
        "grade": 4,
        "class_name": "4B5",
        "subjects": ["Toán", "Tiếng Việt", "Tiếng Anh", "Khoa học"],
        "strengths": ["Tính nhẩm nhanh", "Giỏi hình học", "Tư duy logic tốt"],
        "weaknesses": ["Phân số", "Viết đoạn văn dài", "Chính tả tiếng Anh"],
        "learning_level": "Giỏi",
        "notes": "Thích giải bài tập nâng cao Toán. Cần luyện thêm viết văn.",
    },
    {
        "student_id": "gchat-users/test-student-002",
        "student_name": "Trần Thị Bình",
        "grade": 4,
        "class_name": "4B5",
        "subjects": ["Toán", "Tiếng Việt", "Tiếng Anh", "Khoa học"],
        "strengths": ["Đọc hiểu tiếng Việt tốt", "Viết chữ đẹp", "Sáng tạo"],
        "weaknesses": ["Nhân chia số có nhiều chữ số", "Nghe tiếng Anh", "Đọc bảng biểu"],
        "learning_level": "Khá",
        "notes": "Thích đọc sách. Cần luyện thêm phép tính nhân chia.",
    },
    {
        "student_id": "gchat-users/test-student-003",
        "student_name": "Lê Hoàng Minh",
        "grade": 4,
        "class_name": "4B5",
        "subjects": ["Toán", "Tiếng Việt", "Tiếng Anh", "Khoa học"],
        "strengths": ["Tiếng Anh giao tiếp tốt", "Khoa học tự nhiên", "Ham học hỏi"],
        "weaknesses": ["Giải toán có lời văn", "Tập làm văn miêu tả", "Phân số"],
        "learning_level": "Khá",
        "notes": "Tự tin thuyết trình. Cần hỗ trợ Toán có lời văn.",
    },
    {
        "student_id": "gchat-users/test-student-004",
        "student_name": "Phạm Thanh Hà",
        "grade": 4,
        "class_name": "4B5",
        "subjects": ["Toán", "Tiếng Việt", "Tiếng Anh", "Khoa học"],
        "strengths": ["Chăm chỉ", "Viết văn tốt", "Ngữ pháp tiếng Anh"],
        "weaknesses": ["Hình học — nhận dạng hình", "Đo lường — đơn vị đo", "Tính nhẩm chậm"],
        "learning_level": "Trung bình — Khá",
        "notes": "Cần khuyến khích nhiều hơn. Luyện tập thêm hình học.",
    },
    {
        "student_id": "gchat-users/test-student-005",
        "student_name": "Phan Khánh",
        "grade": 4,
        "class_name": "4B5",
        "subjects": ["Toán", "Tiếng Việt", "Tiếng Anh", "Khoa học"],
        "strengths": ["Nhanh nhẹn", "Tư duy sáng tạo", "Thích thí nghiệm khoa học"],
        "weaknesses": ["Phân số và hỗn số", "Viết chính tả", "Đọc hiểu tiếng Anh"],
        "learning_level": "Khá",
        "notes": "Hay mất tập trung nhưng hiểu bài nhanh. Cần ôn luyện phân số.",
    },
]


async def main() -> None:
    """Insert all dummy profiles."""
    logger.info(f"Seeding {len(DUMMY_PROFILES)} dummy student profiles …")

    success_count = 0
    for profile in DUMMY_PROFILES:
        ok = await store_student_profile(**profile)
        if ok:
            success_count += 1
            logger.info(f"  ✓ {profile['student_name']} ({profile['student_id']})")
        else:
            logger.warning(f"  ✗ Failed: {profile['student_name']}")

    logger.info(f"Done — {success_count}/{len(DUMMY_PROFILES)} profiles stored.")


if __name__ == "__main__":
    asyncio.run(main())
