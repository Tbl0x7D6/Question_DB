"""HTTP client and infrastructure for E2E tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Any

from .config import (
    API_LOG_PATH,
    API_PORT,
    CONTAINER_NAME,
    DB_URL,
    DOWNLOADS_DIR,
    POSTGRES_IMAGE,
    POSTGRES_PORT,
    ROOT_DIR,
    SAMPLES_DIR,
    TMP_DIR,
)


# ── Response helpers ─────────────────────────────────────────────


def parse_json(body: str) -> Any:
    return json.loads(body) if body else None


def paginated_items(body: str) -> list:
    data = parse_json(body)
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    return data


def question_ids_from_body(body: str) -> list[str]:
    return [item["question_id"] for item in paginated_items(body)]


def build_question_fields(
    *,
    description: str,
    difficulty: dict,
    category: str | None = None,
    tags: list[str] | None = None,
    status: str | None = None,
    author: str | None = None,
    reviewers: list[str] | None = None,
) -> dict[str, str]:
    fields: dict[str, str] = {
        "description": description,
        "difficulty": json.dumps(difficulty, ensure_ascii=False),
    }
    if category is not None:
        fields["category"] = category
    if tags is not None:
        fields["tags"] = json.dumps(tags, ensure_ascii=False)
    if status is not None:
        fields["status"] = status
    if author is not None:
        fields["author"] = author
    if reviewers is not None:
        fields["reviewers"] = json.dumps(reviewers, ensure_ascii=False)
    return fields


# ── HTTP Client ──────────────────────────────────────────────────


class ApiClient:
    """Thin HTTP client + test infrastructure manager."""

    def __init__(self) -> None:
        self._api_proc: subprocess.Popen | None = None
        self._api_log: Any = None

    # -- HTTP verbs --

    def get(self, path: str, *, expect: int = 200):
        return self._do("GET", path, expect=expect)

    def delete(self, path: str, *, expect: int = 200):
        return self._do("DELETE", path, expect=expect)

    def post_json(self, path: str, payload: dict, *, expect: int = 200):
        return self._do(
            "POST",
            path,
            expect=expect,
            headers={"content-type": "application/json"},
            body=json.dumps(payload, ensure_ascii=False).encode(),
        )

    def patch_json(self, path: str, payload: dict, *, expect: int = 200):
        return self._do(
            "PATCH",
            path,
            expect=expect,
            headers={"content-type": "application/json"},
            body=json.dumps(payload, ensure_ascii=False).encode(),
        )

    def upload(
        self,
        path: str,
        *,
        fields: dict[str, str] | None = None,
        file_path: Path | None = None,
        method: str = "POST",
        expect: int = 200,
    ):
        boundary = f"----B{uuid.uuid4().hex}"
        raw = bytearray()
        for k, v in (fields or {}).items():
            raw += (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{k}"\r\n\r\n'
                f"{v}\r\n"
            ).encode()
        if file_path is not None:
            raw += (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; '
                f'filename="{file_path.name}"\r\n'
                f"Content-Type: application/zip\r\n\r\n"
            ).encode()
            raw += file_path.read_bytes() + b"\r\n"
        raw += f"--{boundary}--\r\n".encode()
        return self._do(
            method,
            path,
            expect=expect,
            headers={"content-type": f"multipart/form-data; boundary={boundary}"},
            body=bytes(raw),
        )

    def download_zip(
        self,
        path: str,
        payload: dict,
        output: Path,
        *,
        expect: int = 200,
    ) -> tuple[dict, list[str]]:
        req = urllib.request.Request(
            f"http://127.0.0.1:{API_PORT}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode(),
            method="POST",
            headers={"content-type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                data = resp.read()
        except urllib.error.HTTPError as err:
            raise AssertionError(
                f"expected {expect}, got {err.code}: "
                f"{err.read().decode(errors='replace')[:500]}"
            ) from err
        assert status == expect, f"expected {expect}, got {status}"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        with zipfile.ZipFile(output) as zf:
            names = zf.namelist()
            manifest = (
                json.loads(zf.read("manifest.json"))
                if "manifest.json" in names
                else None
            )
        assert manifest is not None, "zip should contain manifest.json"
        return manifest, names

    # -- Infrastructure --

    def prepare_workspace(self) -> None:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    def start_postgres(self) -> None:
        self._docker_rm_if_exists()
        subprocess.run(
            [
                "docker", "run", "-d", "--name", CONTAINER_NAME,
                "-e", "POSTGRES_USER=postgres",
                "-e", "POSTGRES_PASSWORD=postgres",
                "-e", "POSTGRES_DB=qb",
                "-p", f"{POSTGRES_PORT}:5432",
                POSTGRES_IMAGE,
            ],
            cwd=ROOT_DIR, check=True, capture_output=True,
        )
        self._wait_pg()

    def apply_migration(self) -> None:
        sql = (ROOT_DIR / "migrations" / "0001_init_pg.sql").read_bytes()
        subprocess.run(
            [
                "docker", "exec", "-i", CONTAINER_NAME,
                "psql", "-U", "postgres", "-d", "qb",
            ],
            input=sql, cwd=ROOT_DIR, check=True, capture_output=True,
        )

    def start_api(self) -> None:
        self._api_log = API_LOG_PATH.open("wb")
        env = {
            **os.environ,
            "QB_DATABASE_URL": DB_URL,
            "QB_BIND_ADDR": f"127.0.0.1:{API_PORT}",
            "QB_EXPORT_DIR": str(TMP_DIR),
        }
        self._api_proc = subprocess.Popen(
            ["cargo", "run"], cwd=ROOT_DIR, env=env,
            stdout=self._api_log, stderr=subprocess.STDOUT,
        )
        self._wait_api()

    def cleanup(self) -> None:
        if self._api_proc and self._api_proc.poll() is None:
            self._api_proc.terminate()
            try:
                self._api_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._api_proc.kill()
                self._api_proc.wait(timeout=5)
        if self._api_log and not self._api_log.closed:
            self._api_log.close()
        self._docker_rm_if_exists()

    # -- Private --

    def _do(self, method, path, *, expect, headers=None, body=None):
        url = f"http://127.0.0.1:{API_PORT}{path}"
        req = urllib.request.Request(
            url, data=body, method=method, headers=headers or {},
        )
        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                rh = {k.lower(): v for k, v in resp.headers.items()}
                rb = resp.read().decode()
        except urllib.error.HTTPError as err:
            status = err.code
            rh = {k.lower(): v for k, v in err.headers.items()}
            rb = err.read().decode(errors="replace")
        assert status == expect, (
            f"{method} {path}: expected {expect}, got {status}\n{rb[:500]}"
        )
        return status, rb, rh

    def _docker_rm_if_exists(self) -> None:
        r = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=False,
        )
        if CONTAINER_NAME in r.stdout.splitlines():
            subprocess.run(
                ["docker", "rm", "-f", CONTAINER_NAME],
                capture_output=True, check=False,
            )

    def _wait_pg(self) -> None:
        for _ in range(60):
            r = subprocess.run(
                [
                    "docker", "exec", CONTAINER_NAME,
                    "pg_isready", "-U", "postgres", "-d", "qb",
                ],
                capture_output=True, check=False,
            )
            if r.returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError("PostgreSQL did not become ready in 60s")

    def _wait_api(self) -> None:
        for _ in range(120):
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{API_PORT}/health"
                ) as r:
                    if r.status == 200:
                        return
            except Exception:
                time.sleep(1)
        raise RuntimeError("API did not become ready in 120s")
