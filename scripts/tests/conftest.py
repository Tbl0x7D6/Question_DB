"""Pytest fixtures for E2E integration tests.

Session-scoped fixtures provide:
  - ``api``: an ``ApiClient`` with live infrastructure (Docker PG + Rust API)
  - ``state``: a mutable ``E2EState`` for sharing IDs across ordered test phases
"""

from __future__ import annotations

import os

import pytest
from dataclasses import dataclass, field
from pathlib import Path

from .config import INVALID_PAPER_UPLOAD_PATH, SAMPLES_DIR, TMP_DIR
from .fixtures import (
    RealQuestionFixture,
    build_real_experiment_question_zips,
    build_real_theory_question_zips,
    build_sample_paper_appendix_zips,
    build_sample_question_zips,
)
from .session import ApiClient


@dataclass
class E2EState:
    """Mutable shared state across sequential E2E test phases."""

    # Fixtures (populated during session setup)
    synthetic_zips: list[Path] = field(default_factory=list)
    appendix_paths: dict[str, Path] = field(default_factory=dict)
    real_theory_fixtures: list[RealQuestionFixture] = field(default_factory=list)
    real_experiment_fixtures: list[RealQuestionFixture] = field(default_factory=list)

    # Questions (populated by test_1)
    q_ids: list[str] = field(default_factory=list)
    q_by_slug: dict[str, str] = field(default_factory=dict)
    rt_q_ids: list[str] = field(default_factory=list)
    rt_q_by_slug: dict[str, str] = field(default_factory=dict)
    rt_fixtures: dict[str, RealQuestionFixture] = field(default_factory=dict)
    re_q_ids: list[str] = field(default_factory=list)
    re_q_by_slug: dict[str, str] = field(default_factory=dict)
    re_fixtures: dict[str, RealQuestionFixture] = field(default_factory=dict)

    # Papers (populated by test_2)
    theory_paper_ids: list[str] = field(default_factory=list)
    experiment_paper_ids: list[str] = field(default_factory=list)

    @property
    def all_paper_ids(self) -> list[str]:
        return [*self.theory_paper_ids, *self.experiment_paper_ids]

    @property
    def all_real_q_ids(self) -> list[str]:
        return [*self.rt_q_ids, *self.re_q_ids]

    @property
    def total_question_count(self) -> int:
        return len(self.q_ids) + len(self.all_real_q_ids)


@pytest.fixture(scope="session")
def state() -> E2EState:
    return E2EState()


@pytest.fixture(scope="session")
def api(state: E2EState):
    """Start infrastructure, build fixtures, yield API client, cleanup."""
    client = ApiClient()
    client.prepare_workspace()

    # Build fixture zip files (local, no API needed)
    state.synthetic_zips = build_sample_question_zips(SAMPLES_DIR)
    state.appendix_paths = build_sample_paper_appendix_zips(
        SAMPLES_DIR, INVALID_PAPER_UPLOAD_PATH,
    )
    state.real_theory_fixtures = build_real_theory_question_zips(TMP_DIR, SAMPLES_DIR)
    state.real_experiment_fixtures = build_real_experiment_question_zips(
        TMP_DIR, SAMPLES_DIR,
    )

    # Start infrastructure (skip with QB_E2E_SKIP_INFRA=1 if already running)
    skip_infra = os.environ.get("QB_E2E_SKIP_INFRA")
    if not skip_infra:
        client.start_postgres()
        client.apply_migration()
        client.start_api()

    # Verify API is reachable
    client.get("/health")

    yield client

    if not skip_infra:
        client.cleanup()
