from __future__ import annotations

import io
import zipfile
from pathlib import Path


def validate_question_bundle(
    manifest: dict,
    names: list[str],
    question_ids: list[str],
) -> None:
    assert manifest["kind"] == "question_bundle"
    assert manifest["question_count"] == len(question_ids)

    bundled_ids = [item["question_id"] for item in manifest["questions"]]
    assert bundled_ids == question_ids, "bundle ids should preserve request order"

    for item in manifest["questions"]:
        prefix = f"{item['metadata']['description']}_"
        assert item["directory"].startswith(prefix)
        assert item["directory"] != item["question_id"]
        file_paths = {e["zip_path"] for e in item["files"]}
        assert all(p.startswith(f"{item['directory']}/") for p in file_paths)
        assert any(p.endswith(".tex") for p in file_paths)
        assert any("/assets/" in p for p in file_paths)
        assert all(p in names for p in file_paths)


def validate_paper_bundle(
    manifest: dict,
    names: list[str],
    paper_ids: list[str],
    bundle_path: Path,
    expected_papers: dict[str, dict],
    expected_template_source: str,
    expected_category: str,
    sample_problem_title: str,
) -> None:
    assert manifest["kind"] == "paper_bundle"
    assert manifest["paper_count"] == len(paper_ids)

    bundled_ids = [item["paper_id"] for item in manifest["papers"]]
    assert bundled_ids == paper_ids, "bundle ids should preserve request order"

    with zipfile.ZipFile(bundle_path) as archive:
        for item in manifest["papers"]:
            exp = expected_papers[item["paper_id"]]
            assert item["directory"].startswith(
                f"{item['metadata']['description']}_"
            )
            assert item["directory"] != item["paper_id"]
            assert item["template_source"] == expected_template_source
            assert item["metadata"]["title"] == exp["title"]
            assert item["metadata"]["subtitle"] == exp["subtitle"]
            assert item["metadata"]["authors"] == exp["authors"]
            assert item["metadata"]["reviewers"] == exp["reviewers"]

            # appendix round-trip
            af = item["append_file"]
            assert af["file_kind"] == "appendix"
            assert af["zip_path"] == f"{item['directory']}/append.zip"
            assert af["original_path"] == exp["appendix_path"].name
            assert af["zip_path"] in names
            assert archive.read(af["zip_path"]) == exp["appendix_path"].read_bytes()

            with zipfile.ZipFile(exp["appendix_path"]) as expected_zf:
                expected_entries = sorted(expected_zf.namelist())
            with zipfile.ZipFile(
                io.BytesIO(archive.read(af["zip_path"]))
            ) as actual_zf:
                assert sorted(actual_zf.namelist()) == expected_entries

            # main.tex rendering
            mt = item["main_tex_file"]
            assert mt["zip_path"] == f"{item['directory']}/main.tex"
            assert mt["zip_path"] in names
            assert mt["original_path"] == expected_template_source
            tex = archive.read(mt["zip_path"]).decode()
            assert f"\\cphostitle{{{exp['title']}}}" in tex
            assert f"\\cphossubtitle{{{exp['subtitle']}}}" in tex
            assert tex.count("\\begin{problem}") == len(exp["question_ids"])
            assert sample_problem_title not in tex
            assert "X~X\\quad XXX\\quad XXX" not in tex
            assert "Y~Y\\quad YYY\\quad YYY" not in tex

            # question order and metadata
            actual_qids = [q["question_id"] for q in item["questions"]]
            assert actual_qids == exp["question_ids"]
            for seq, q in enumerate(item["questions"], start=1):
                assert q["sequence"] == seq
                assert q["asset_prefix"] == f"p{seq}-"
                assert q["source_tex_path"] == "main.tex"
                assert q["metadata"]["category"] == expected_category

            # merged assets
            assert len(item["assets"]) == exp["asset_total"]
            for asset in item["assets"]:
                assert asset["zip_path"] in names
                assert asset["zip_path"].startswith(
                    f"{item['directory']}/assets/"
                )
                assert asset["source_question_id"] in exp["question_ids"]
