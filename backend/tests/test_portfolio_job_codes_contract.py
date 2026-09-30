"""Vertrag: Portfolio-Jobcodes Backend ↔ Frontend (TF-987).

Die Portfolio-Tasks schreiben Codes wie ``portfolio_grading_timeout`` in
``job.error_log`` bzw. in die ``warnings`` eines Phasenergebnisses. Sie kommen
nie als HTTP-``error_code`` an, deshalb deckt ``test_error_codes_contract.py``
sie nicht ab. Das Frontend übersetzt sie über die Liste
``PORTFOLIO_JOB_CODES`` in ``core/frontend/src/types/portfolio.ts``; ein Code,
der dort fehlt, landet im generischen Fallback und zeigt den deutschen
``reason`` auch in EN/FR/IT.

Im ``core/``-Mirror fehlt ``premium/`` — dann gibt es keine Quelle und der Test
wird übersprungen.
"""

from __future__ import annotations

import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PREMIUM_BACKEND = REPO_ROOT / "premium" / "backend"
FRONTEND_TYPES = REPO_ROOT / "core/frontend/src/types/portfolio.ts"

CODE_PATTERN = re.compile(
    r"[\"'](portfolio_(?:ingestion|github|classification|grading)_[a-z_]+)[\"']"
)


def _backend_codes() -> set[str]:
    codes: set[str] = set()
    for sub in ("tasks", "services", "api"):
        for path in sorted((PREMIUM_BACKEND / sub).rglob("*.py")):
            codes.update(CODE_PATTERN.findall(path.read_text(encoding="utf-8")))
    return codes


def _frontend_codes() -> set[str]:
    source = FRONTEND_TYPES.read_text(encoding="utf-8")
    block = re.search(
        r"export const PORTFOLIO_JOB_CODES = \[(.*?)\] as const;", source, re.S
    )
    assert block, (
        f"PORTFOLIO_JOB_CODES nicht in {FRONTEND_TYPES} gefunden — "
        "umbenannt oder verschoben? Diesen Test nachziehen."
    )
    return set(CODE_PATTERN.findall(block.group(1)))


@pytest.mark.skipif(not PREMIUM_BACKEND.is_dir(), reason="core/-Mirror: premium/ fehlt")
def test_portfolio_jobcodes_backend_und_frontend_gleich():
    backend = _backend_codes()
    frontend = _frontend_codes()

    assert backend, "Scan findet keine Portfolio-Jobcodes — Muster veraltet?"
    assert not backend - frontend, (
        "Jobcodes im Backend, die das Frontend nicht übersetzt — in "
        "PORTFOLIO_JOB_CODES und pages.portfolio.jobCodes (4 Sprachen) "
        f"ergänzen: {sorted(backend - frontend)}"
    )
    assert not frontend - backend, (
        "Jobcodes im Frontend, die kein Backend-Pfad mehr schreibt: "
        f"{sorted(frontend - backend)}"
    )
