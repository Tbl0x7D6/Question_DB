"""Export, quality-check, and bundle endpoint tests (positive + negative)."""

from __future__ import annotations

from .config import EXPORT_PATH, QUALITY_PATH
from .session import parse_json


# ── Tests ────────────────────────────────────────────────────────


def test_export_jsonl(api, state):
    _, body, _ = api.post_json(
        "/exports/run",
        {
            "format": "jsonl",
            "public": False,
            "output_path": EXPORT_PATH.name,
        },
    )
    resp = parse_json(body)
    assert resp["exported_questions"] == state.total_question_count


def test_export_path_traversal(api):
    """Reject directory-traversal and absolute paths."""
    api.post_json(
        "/exports/run",
        {"format": "jsonl", "output_path": "../../../etc/passwd"},
        expect=400,
    )
    api.post_json(
        "/exports/run",
        {"format": "jsonl", "output_path": "/absolute/path.jsonl"},
        expect=400,
    )


def test_quality_check(api):
    _, body, _ = api.post_json(
        "/quality-checks/run", {"output_path": QUALITY_PATH.name},
    )
    assert "empty_papers" in parse_json(body)["report"]


def test_quality_check_path_traversal(api):
    api.post_json(
        "/quality-checks/run",
        {"output_path": "../../etc/shadow"},
        expect=400,
    )


def test_question_bundle_validation(api):
    """Empty and malformed IDs."""
    api.post_json("/questions/bundles", {"question_ids": []}, expect=400)
    api.post_json(
        "/questions/bundles", {"question_ids": ["not-a-uuid"]}, expect=400,
    )


def test_paper_bundle_validation(api):
    api.post_json("/papers/bundles", {"paper_ids": []}, expect=400)
    api.post_json(
        "/papers/bundles", {"paper_ids": ["not-a-uuid"]}, expect=400,
    )
