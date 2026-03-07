"""
Vector database integration tests.

Tests the full round-trip for both collections:
  1. Grading results — store → search by student ID → search without filter
  2. Document embeddings — insert → search → cleanup

Run from the backend directory:
    python -m scripts.test_vector_search

The script exits 0 on success, 1 if any test fails.
"""

import asyncio
import sys
from datetime import datetime, timezone

from database.milvus_client import milvus_client
from database.repositories.grading_repository import (
    GRADING_COLLECTION,
    store_grading_result,
    search_student_grades,
)
from utils.embeddings import generate_single_embedding, generate_embeddings
from utils.logger import logger

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

STUDENT_A = "users/test-student-001"
STUDENT_B = "users/test-student-002"

GRADING_FIXTURE = {
    "student_id": STUDENT_A,
    "student_name": "Nguyễn Văn An",
    "subject": "Toán",
    "assignment_title": "Bài kiểm tra chương 3 – Phân số",
    "score": 8.5,
    "max_score": 10.0,
    "feedback": "Con làm bài tốt, trình bày rõ ràng.",
    "detailed_feedback": (
        "Cô Hana rất vui vì con đã hiểu đúng cách quy đồng mẫu số. "
        "Phần tính toán phân số hỗn số còn một lỗi nhỏ ở bài 4. "
        "Nhìn chung bài làm rất tốt, con cố gắng kiểm tra lại kết quả "
        "trước khi nộp nhé."
    ),
    "strengths": ["Trình bày rõ ràng", "Quy đồng mẫu số đúng"],
    "improvements": ["Kiểm tra lại phép tính phân số hỗn số"],
    "graded_at": datetime.now(timezone.utc).isoformat(),
}

SEARCH_QUERIES = [
    ("Bài kiểm tra vừa rồi con được bao nhiêu điểm?", True),   # should find A's record
    ("Con làm sai chỗ nào trong bài?", True),                  # should find A's feedback
    ("Điểm mạnh của con là gì?", True),                        # should find A's strengths
    ("Hôm nay thời tiết thế nào?", False),                     # unrelated — low similarity, may still return rows
]

PASS = "✓ PASS"
FAIL = "✗ FAIL"

failed = 0


def ok(msg: str) -> None:
    logger.info(f"{PASS}  {msg}")


def fail(msg: str) -> None:
    global failed
    failed += 1
    logger.error(f"{FAIL}  {msg}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    logger.info(f"\n{'─' * 60}")
    logger.info(f"  {title}")
    logger.info(f"{'─' * 60}")


# ---------------------------------------------------------------------------
# Test: Milvus connectivity
# ---------------------------------------------------------------------------

def test_connectivity() -> None:
    section("1. Milvus connectivity")

    if milvus_client.connected:
        ok("MilvusClient.connected == True")
    else:
        fail("MilvusClient is not connected — check MILVUS_URI / MILVUS_HOST in .env")


# ---------------------------------------------------------------------------
# Test: Embedding generation
# ---------------------------------------------------------------------------

async def test_embeddings() -> None:
    section("2. Embedding generation")

    text = "Kết quả chấm bài của học sinh. Điểm: 8.5/10."
    try:
        emb = await generate_single_embedding(text)
        if len(emb) == 768:
            ok(f"Single embedding: {len(emb)}-dim vector")
        else:
            fail(f"Expected 768-dim, got {len(emb)}-dim")
    except Exception as e:
        fail(f"generate_single_embedding raised: {e}")

    texts = ["Câu hỏi một.", "Câu hỏi hai.", "Câu hỏi ba."]
    try:
        embs = await generate_embeddings(texts)
        if len(embs) == len(texts) and all(len(e) == 768 for e in embs):
            ok(f"Batch embeddings: {len(embs)} × 768-dim")
        else:
            fail(f"Batch embedding shape mismatch: got {[len(e) for e in embs]}")
    except Exception as e:
        fail(f"generate_embeddings raised: {e}")


# ---------------------------------------------------------------------------
# Test: Grading collection — store
# ---------------------------------------------------------------------------

async def test_store_grading() -> None:
    section("3. Store grading result")

    if not milvus_client.connected:
        logger.warning("Skipping — Milvus not connected")
        return

    # Ensure collection exists
    milvus_client.create_grading_collection(GRADING_COLLECTION)

    success = await store_grading_result(**GRADING_FIXTURE)
    if success:
        ok(f"Stored grading result for {GRADING_FIXTURE['student_name']} ({GRADING_FIXTURE['score']}/{GRADING_FIXTURE['max_score']})")
    else:
        fail("store_grading_result returned False")

    # Store a second record for a different student (to test ID filtering later)
    success2 = await store_grading_result(
        student_id=STUDENT_B,
        student_name="Trần Thị Bình",
        subject="Tiếng Anh",
        assignment_title="Unit 5 Test",
        score=7.0,
        max_score=10.0,
        feedback="Con cần cải thiện ngữ pháp.",
        detailed_feedback="Vocabulary tốt nhưng cấu trúc câu cần ôn thêm.",
        strengths=["Từ vựng phong phú"],
        improvements=["Cấu trúc câu", "Thì hiện tại hoàn thành"],
    )
    if success2:
        ok(f"Stored second grading result for student B")
    else:
        fail("store_grading_result (student B) returned False")


# ---------------------------------------------------------------------------
# Test: Grading collection — search with student filter
# ---------------------------------------------------------------------------

async def test_search_with_filter() -> None:
    section("4. Search with student_id filter")

    if not milvus_client.connected:
        logger.warning("Skipping — Milvus not connected")
        return

    for query, expect_results in SEARCH_QUERIES:
        results = await search_student_grades(
            query=query,
            student_id=STUDENT_A,
            top_k=3,
        )

        # All returned rows must belong to STUDENT_A
        wrong_student = [r for r in results if r.get("student_id") != STUDENT_A]
        if wrong_student:
            fail(f"Filter leak — got rows for other students: {[r['student_id'] for r in wrong_student]}")
        else:
            ok(f"Query '{query[:45]}...' → {len(results)} result(s) (all student A)")

        if expect_results and results:
            top = results[0]
            meta = top.get("metadata", {})
            logger.info(
                f"    Top hit: {top.get('student_name')} | "
                f"{top.get('score')}/{top.get('max_score')} | "
                f"sim={top.get('similarity', 0):.4f} | "
                f"feedback='{meta.get('feedback', '')[:50]}'"
            )


# ---------------------------------------------------------------------------
# Test: Grading collection — search without filter
# ---------------------------------------------------------------------------

async def test_search_no_filter() -> None:
    section("5. Search without student_id filter (global)")

    if not milvus_client.connected:
        logger.warning("Skipping — Milvus not connected")
        return

    results = await search_student_grades(
        query="Điểm bài kiểm tra",
        student_id=None,
        top_k=5,
    )

    student_ids = {r.get("student_id") for r in results}
    if len(student_ids) > 1:
        ok(f"Global search returned results for {len(student_ids)} distinct students: {student_ids}")
    elif len(results) > 0:
        ok(f"Global search returned {len(results)} result(s) (only 1 student in DB is fine)")
    else:
        fail("Global search returned no results — check that store test ran first")


# ---------------------------------------------------------------------------
# Test: Document collection — insert and search
# ---------------------------------------------------------------------------

async def test_document_collection() -> None:
    section("6. Document collection — insert & search")

    if not milvus_client.connected:
        logger.warning("Skipping — Milvus not connected")
        return

    collection = milvus_client.create_document_collection("documents")
    if collection:
        ok(f"Document collection ready: {collection.name}")
    else:
        fail("create_document_collection returned None")
        return

    # Generate embeddings for sample chunks
    chunks = [
        "Bài học hôm nay: Phân số và các phép tính cơ bản.",
        "Ví dụ: 1/2 + 1/3 = 5/6. Quy đồng mẫu số là bước đầu tiên.",
        "Bài tập về nhà: Trang 42, bài 1 đến bài 5.",
    ]
    doc_id = "test-doc-vector-search-001"

    try:
        embeddings = await generate_embeddings(chunks)
        inserted_ids = milvus_client.insert_embeddings(
            collection_name="documents",
            document_ids=[doc_id] * len(chunks),
            chunk_indices=list(range(len(chunks))),
            texts=chunks,
            embeddings=embeddings,
            metadata=[{"subject": "Toán", "grade": 4}] * len(chunks),
        )
        if len(inserted_ids) == len(chunks):
            ok(f"Inserted {len(inserted_ids)} document chunks (doc_id={doc_id})")
        else:
            fail(f"Expected {len(chunks)} inserted IDs, got {len(inserted_ids)}")
    except Exception as e:
        fail(f"insert_embeddings raised: {e}")
        return

    # Search
    try:
        query_emb = await generate_single_embedding("Bài tập về nhà trang 42")
        results = milvus_client.search(
            collection_name="documents",
            query_embedding=query_emb,
            top_k=3,
        )
        if results:
            top = results[0]
            ok(
                f"Document search: top hit chunk {top.get('chunk_index')} "
                f"(sim={top.get('score', 0):.4f}) — '{top.get('text', '')[:50]}...'"
            )
        else:
            fail("Document search returned no results")
    except Exception as e:
        fail(f"milvus_client.search raised: {e}")

    # Cleanup test doc
    try:
        milvus_client.delete_by_document_id("documents", doc_id)
        ok(f"Cleaned up test document {doc_id}")
    except Exception as e:
        logger.warning(f"Cleanup failed (non-critical): {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    logger.info("=" * 60)
    logger.info("  Vector Database Integration Tests")
    logger.info("=" * 60)

    await test_embeddings()
    test_connectivity()
    await test_store_grading()
    await test_search_with_filter()
    await test_search_no_filter()
    await test_document_collection()

    logger.info("\n" + "=" * 60)
    if failed == 0:
        logger.info("  ALL TESTS PASSED")
    else:
        logger.error(f"  {failed} TEST(S) FAILED")
    logger.info("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
