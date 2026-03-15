from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .utils import load_json, sha256_file

ALLOWED_QUESTION_KEYS = {
    "question_id",
    "question_no",
    "paper_index",
    "category",
    "latex_path",
    "answer_latex_path",
    "latex_anchor",
    "search_text",
    "status",
    "tags",
    "assets",
    "notes",
}

ALLOWED_PAPER_TYPES = {"regular", "semifinal", "final", "other"}


@dataclass(slots=True)
class ValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def load_bundle(bundle_path: Path) -> tuple[dict, list[dict]]:
    manifest = load_json(bundle_path / "manifest.json")
    question_dir = bundle_path / "questions"
    questions = [load_json(path) for path in sorted(question_dir.glob("*.json"))]
    return manifest, questions


def validate_bundle(bundle_path: Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    manifest, questions = load_bundle(bundle_path)

    required_manifest_keys = {"bundle_name", "run_label", "paper"}
    missing_manifest = required_manifest_keys - set(manifest)
    if missing_manifest:
        errors.append(f"manifest.json 缺少字段: {sorted(missing_manifest)}")
    if not questions:
        errors.append("questions/ 下没有题目 JSON 文件。")

    paper = manifest.get("paper", {})
    required_paper_keys = {"paper_id", "edition", "paper_type", "title", "paper_latex_path"}
    missing_paper = required_paper_keys - set(paper)
    if missing_paper:
        errors.append(f"paper 配置缺少字段: {sorted(missing_paper)}")
    if paper.get("paper_type") not in ALLOWED_PAPER_TYPES:
        errors.append("paper.paper_type 必须是 regular、semifinal、final 或 other。")
    paper_latex_path = paper.get("paper_latex_path")
    if paper_latex_path and not (bundle_path / paper_latex_path).exists():
        errors.append(f"paper_latex_path 不存在: {paper_latex_path}")
    source_pdf_path = paper.get("source_pdf_path")
    if source_pdf_path and not (bundle_path / source_pdf_path).exists():
        warnings.append(f"source_pdf_path 不存在: {source_pdf_path}")

    score_workbooks = manifest.get("score_workbooks", [])
    seen_workbook_ids: set[str] = set()
    for workbook in score_workbooks:
        workbook_id = workbook.get("workbook_id")
        if not workbook_id:
            errors.append("score_workbooks 中存在缺少 workbook_id 的条目。")
            continue
        if workbook_id in seen_workbook_ids:
            errors.append(f"重复的 workbook_id: {workbook_id}")
        seen_workbook_ids.add(workbook_id)
        for key in ("exam_session", "workbook_kind", "file_path"):
            if key not in workbook:
                errors.append(f"workbook {workbook_id} 缺少字段: {key}")
        file_path = workbook.get("file_path")
        if file_path and not (bundle_path / file_path).exists():
            errors.append(f"workbook 文件不存在: {file_path}")

    seen_ids: set[str] = set()
    seen_numbers: set[str] = set()
    seen_indexes: set[int] = set()

    for idx, question in enumerate(questions, start=1):
        file_label = f"题目 #{idx}"
        required_keys = {"question_id", "question_no", "paper_index", "category", "latex_path", "status", "tags", "assets"}
        missing = required_keys - set(question)
        if missing:
            errors.append(f"{file_label} 缺少字段: {sorted(missing)}")
        unknown = set(question) - ALLOWED_QUESTION_KEYS
        if unknown:
            warnings.append(f"{file_label} 包含未识别字段: {sorted(unknown)}")

        question_id = question.get("question_id")
        if question_id:
            if question_id in seen_ids:
                errors.append(f"重复的 question_id: {question_id}")
            seen_ids.add(question_id)

        question_no = question.get("question_no")
        if question_no:
            if question_no in seen_numbers:
                warnings.append(f"同一个 bundle 中出现重复题号: {question_no}")
            seen_numbers.add(question_no)

        paper_index = question.get("paper_index")
        if isinstance(paper_index, int):
            if paper_index in seen_indexes:
                errors.append(f"重复的 paper_index: {paper_index}")
            seen_indexes.add(paper_index)
        else:
            errors.append(f"{question_id or file_label} 的 paper_index 必须是整数。")

        if question.get("category") not in {"theory", "experiment"}:
            errors.append(f"{question_id or file_label} 的 category 必须为 theory 或 experiment。")
        if question.get("status") not in {"raw", "reviewed", "published"}:
            errors.append(f"{question_id or file_label} 的 status 必须为 raw/reviewed/published。")

        latex_path = question.get("latex_path")
        if latex_path and not (bundle_path / latex_path).exists():
            errors.append(f"{question_id or file_label} 的 latex_path 不存在: {latex_path}")
        answer_latex_path = question.get("answer_latex_path")
        if answer_latex_path and not (bundle_path / answer_latex_path).exists():
            errors.append(f"{question_id or file_label} 的 answer_latex_path 不存在: {answer_latex_path}")

        for asset in question.get("assets", []):
            rel_path = asset.get("file_path")
            if not rel_path:
                errors.append(f"{question_id or file_label} 的 asset 缺少 file_path。")
                continue
            asset_path = bundle_path / rel_path
            if not asset_path.exists():
                errors.append(f"{question_id or file_label} 的 asset 不存在: {rel_path}")
            else:
                expected_sha = asset.get("sha256")
                actual_sha = sha256_file(asset_path)
                if expected_sha and expected_sha.lower() != actual_sha.lower():
                    errors.append(f"{question_id or file_label} 的 asset 校验失败: {rel_path}")
                if not expected_sha:
                    warnings.append(f"{question_id or file_label} 的 asset 未填写 sha256: {rel_path}")

    return ValidationResult(errors=errors, warnings=warnings)
