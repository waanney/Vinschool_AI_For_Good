"""
Unit tests for the submission store.

Tests cover:
- add_submission(): creates and stores submission with correct fields
- get_submissions(): returns sorted list (newest first)
- get_unviewed_count(): counts unviewed submissions
- mark_viewed(): marks a submission as viewed
- clear_submissions(): clears the store
"""

import pytest
from services.chat.submission_store import (
    submission_store,
    add_submission,
    get_submissions,
    get_unviewed_count,
    mark_viewed,
    clear_submissions,
)


@pytest.fixture(autouse=True)
def clear_store():
    """Clear submission store before and after each test."""
    submission_store.clear()
    yield
    submission_store.clear()


class TestAddSubmission:
    """Tests for add_submission()."""

    def test_creates_submission_with_correct_fields(self):
        """Submission has all required fields set."""
        sub = add_submission(
            student_id="users/123",
            student_name="Quang Bách",
            score=8.5,
            max_score=10.0,
            feedback="Tốt lắm!",
            attachment_paths=["/tmp/img1.jpg"],
        )
        assert sub["student_id"] == "users/123"
        assert sub["student_name"] == "Quang Bách"
        assert sub["score"] == 8.5
        assert sub["max_score"] == 10.0
        assert sub["feedback"] == "Tốt lắm!"
        assert sub["attachment_paths"] == ["/tmp/img1.jpg"]
        assert sub["is_viewed"] is False
        assert sub["id"] is not None

    def test_default_subject_and_title(self):
        """Default subject is Mathematics, default title is Homework Submission."""
        sub = add_submission(
            student_id="u1",
            student_name="A",
            score=5.0,
            max_score=10.0,
            feedback="",
            attachment_paths=[],
        )
        assert sub["subject"] == "Mathematics"
        assert sub["assignment_title"] == "Homework Submission"

    def test_custom_subject_and_title(self):
        """Custom subject and title are stored."""
        sub = add_submission(
            student_id="u1",
            student_name="A",
            score=5.0,
            max_score=10.0,
            feedback="",
            attachment_paths=[],
            subject="Science",
            assignment_title="Lab Report",
        )
        assert sub["subject"] == "Science"
        assert sub["assignment_title"] == "Lab Report"

    def test_stores_in_submission_store(self):
        """Adding a submission appends to the module-level store."""
        assert len(submission_store) == 0
        add_submission(
            student_id="u1",
            student_name="A",
            score=5.0,
            max_score=10.0,
            feedback="",
            attachment_paths=[],
        )
        assert len(submission_store) == 1

    def test_multiple_submissions_accumulate(self):
        """Multiple adds increase the store size."""
        for i in range(3):
            add_submission(
                student_id=f"u{i}",
                student_name=f"Student {i}",
                score=float(i),
                max_score=10.0,
                feedback="",
                attachment_paths=[],
            )
        assert len(submission_store) == 3

    def test_details_stored(self):
        """Optional details dict is stored."""
        sub = add_submission(
            student_id="u1",
            student_name="A",
            score=7.0,
            max_score=10.0,
            feedback="Good",
            attachment_paths=[],
            details={"strengths": ["Quick"], "improvements": ["Accuracy"]},
        )
        assert sub["details"]["strengths"] == ["Quick"]


class TestGetSubmissions:
    """Tests for get_submissions()."""

    def test_returns_sorted_newest_first(self):
        """Submissions are returned sorted by graded_at descending."""
        import time

        add_submission(
            student_id="u1", student_name="First",
            score=5.0, max_score=10.0, feedback="", attachment_paths=[],
        )
        time.sleep(0.01)  # Ensure different timestamps
        add_submission(
            student_id="u2", student_name="Second",
            score=8.0, max_score=10.0, feedback="", attachment_paths=[],
        )

        subs = get_submissions()
        assert subs[0]["student_name"] == "Second"
        assert subs[1]["student_name"] == "First"

    def test_empty_store_returns_empty_list(self):
        """Empty store returns empty list."""
        assert get_submissions() == []


class TestGetUnviewedCount:
    """Tests for get_unviewed_count()."""

    def test_all_unviewed_initially(self):
        """All new submissions are unviewed."""
        add_submission(
            student_id="u1", student_name="A",
            score=5.0, max_score=10.0, feedback="", attachment_paths=[],
        )
        add_submission(
            student_id="u2", student_name="B",
            score=5.0, max_score=10.0, feedback="", attachment_paths=[],
        )
        assert get_unviewed_count() == 2

    def test_viewed_not_counted(self):
        """Viewed submissions are not counted."""
        sub = add_submission(
            student_id="u1", student_name="A",
            score=5.0, max_score=10.0, feedback="", attachment_paths=[],
        )
        mark_viewed(sub["id"])
        assert get_unviewed_count() == 0

    def test_empty_store_returns_zero(self):
        """Empty store returns 0."""
        assert get_unviewed_count() == 0


class TestMarkViewed:
    """Tests for mark_viewed()."""

    def test_marks_existing_submission(self):
        """Marking an existing submission sets is_viewed to True."""
        sub = add_submission(
            student_id="u1", student_name="A",
            score=5.0, max_score=10.0, feedback="", attachment_paths=[],
        )
        assert mark_viewed(sub["id"]) is True
        assert submission_store[0]["is_viewed"] is True

    def test_returns_false_for_nonexistent(self):
        """Returns False for a nonexistent submission ID."""
        assert mark_viewed("nonexistent-id") is False


class TestClearSubmissions:
    """Tests for clear_submissions()."""

    def test_clears_all(self):
        """Clear removes all submissions."""
        add_submission(
            student_id="u1", student_name="A",
            score=5.0, max_score=10.0, feedback="", attachment_paths=[],
        )
        clear_submissions()
        assert len(submission_store) == 0


# Run with: pytest tests/test_submission_store.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
