from __future__ import annotations

import difflib
from pathlib import Path

from .bundle import load_bundle, validate_bundle
from .db import connect
from .utils import dumps_json, sha256_file, utc_now_iso
from .workbooks import upsert_score_workbook


def _find_similar_questions(conn, search_text: str, threshold: float = 0.92) -> list[str]:
    matches: list[str] = []
    if not search_text:
        return matches
    for row in conn.execute("SELECT question_id, COALESCE(search_text, '') AS search_text FROM questions").fetchall():
        if not row["search_text"]:
            continue
        ratio = difflib.SequenceMatcher(a=search_text, b=row["search_text"]).ratio()
        if ratio >= threshold:
            matches.append(f"{row['question_id']} ({ratio:.3f})")
    return matches


def _project_root_from_bundle(bundle_path: Path) -> Path:
    return bundle_path.resolve().parents[1]


def _relative_to_project(project_root: Path, target_path: Path) -> str:
    return target_path.resolve().relative_to(project_root).as_posix()


def import_bundle(bundle_path: Path, db_path: Path, dry_run: bool = True, allow_similar: bool = False) -> dict:
    validation = validate_bundle(bundle_path)
    manifest, questions = load_bundle(bundle_path)
    warnings = list(validation.warnings)
    errors = list(validation.errors)
    imported_questions = 0
    imported_assets = 0
    imported_workbooks = 0
    started_at = utc_now_iso()
    finished_at = started_at
    project_root = _project_root_from_bundle(bundle_path)

    with connect(db_path) as conn:
        paper = manifest["paper"]
        for question in questions:
            existing = conn.execute(
                "SELECT question_id FROM questions WHERE paper_id = ? AND question_no = ?",
                (paper["paper_id"], question["question_no"]),
            ).fetchone()
            if existing and existing["question_id"] != question["question_id"]:
                errors.append(
                    f"题号冲突: 同一试卷 {paper['paper_id']} 的题号 {question['question_no']} 已被 {existing['question_id']} 使用。"
                )
            similar = _find_similar_questions(conn, question.get("search_text", ""))
            if similar and question["question_id"] not in {item.split()[0] for item in similar}:
                message = f"{question['question_id']} 与已有题目文本索引高度相似: {', '.join(similar)}"
                if allow_similar:
                    warnings.append(message)
                else:
                    errors.append(message)

        status = "failed" if errors else ("dry_run" if dry_run else "committed")
        details = {
            "bundle_name": manifest.get("bundle_name"),
            "paper_id": paper.get("paper_id"),
            "warnings": warnings,
            "errors": errors,
        }
        if not errors and not dry_run:
            now = utc_now_iso()
            question_index = [
                {
                    "paper_index": question["paper_index"],
                    "question_id": question["question_id"],
                    "question_no": question["question_no"],
                    "latex_path": question["latex_path"],
                }
                for question in sorted(questions, key=lambda item: item["paper_index"])
            ]
            paper_latex_path = _relative_to_project(project_root, bundle_path / paper["paper_latex_path"])
            source_pdf_path = None
            if paper.get("source_pdf_path"):
                source_pdf_path = _relative_to_project(project_root, bundle_path / paper["source_pdf_path"])
            conn.execute(
                """
                INSERT OR REPLACE INTO papers (
                    paper_id, edition, paper_type, title, paper_latex_path, source_pdf_path,
                    question_index_json, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM papers WHERE paper_id = ?), ?), ?)
                """,
                (
                    paper["paper_id"],
                    paper["edition"],
                    paper["paper_type"],
                    paper["title"],
                    paper_latex_path,
                    source_pdf_path,
                    dumps_json(question_index),
                    paper.get("notes"),
                    paper["paper_id"],
                    now,
                    now,
                ),
            )
            for question in questions:
                latex_path = _relative_to_project(project_root, bundle_path / question["latex_path"])
                answer_latex_path = None
                if question.get("answer_latex_path"):
                    answer_latex_path = _relative_to_project(project_root, bundle_path / question["answer_latex_path"])
                conn.execute(
                    """
                    INSERT OR REPLACE INTO questions (
                        question_id, paper_id, paper_index, question_no, category,
                        latex_path, answer_latex_path, latex_anchor, search_text,
                        status, tags_json, notes, created_at, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        COALESCE((SELECT created_at FROM questions WHERE question_id = ?), ?), ?
                    )
                    """,
                    (
                        question["question_id"],
                        paper["paper_id"],
                        question["paper_index"],
                        question["question_no"],
                        question["category"],
                        latex_path,
                        answer_latex_path,
                        question.get("latex_anchor"),
                        question.get("search_text"),
                        question["status"],
                        dumps_json(question.get("tags", [])),
                        question.get("notes"),
                        question["question_id"],
                        now,
                        now,
                    ),
                )
                imported_questions += 1
                conn.execute("DELETE FROM question_assets WHERE question_id = ?", (question["question_id"],))
                for asset in question.get("assets", []):
                    asset_path = (bundle_path / asset["file_path"]).resolve()
                    stored_path = asset_path.relative_to(project_root).as_posix()
                    conn.execute(
                        """
                        INSERT INTO question_assets (
                            asset_id, question_id, kind, file_path, sha256, caption, sort_order, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            asset["asset_id"],
                            question["question_id"],
                            asset["kind"],
                            stored_path,
                            asset.get("sha256") or sha256_file(asset_path),
                            asset.get("caption"),
                            asset.get("sort_order", 0),
                            now,
                        ),
                    )
                    imported_assets += 1
            conn.commit()
            for workbook in manifest.get("score_workbooks", []):
                upsert_score_workbook(db_path, paper_id=paper["paper_id"], workbook=workbook, bundle_path=bundle_path)
                imported_workbooks += 1
            finished_at = utc_now_iso()
        else:
            finished_at = utc_now_iso()

        conn.execute(
            """
            INSERT INTO import_runs (
                run_label, bundle_path, dry_run, status, item_count, warning_count, error_count,
                details_json, started_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                manifest.get("run_label", bundle_path.name),
                str(bundle_path.resolve()),
                1 if dry_run else 0,
                status,
                len(questions) + len(manifest.get("score_workbooks", [])),
                len(warnings),
                len(errors),
                dumps_json(details),
                started_at,
                finished_at,
            ),
        )
        conn.commit()

    return {
        "bundle_name": manifest.get("bundle_name"),
        "paper_id": manifest["paper"]["paper_id"],
        "status": status,
        "question_count": len(questions),
        "imported_questions": imported_questions,
        "imported_assets": imported_assets,
        "imported_workbooks": imported_workbooks,
        "warnings": warnings,
        "errors": errors,
    }
