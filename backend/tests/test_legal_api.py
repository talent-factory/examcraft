"""Tests for the public compliance-document API (TF-746, ``api.legal``).

These endpoints are unauthenticated by design (prospective school
customers need to download the AVV/TOM before signing up), so — unlike
most API tests in this repo — no auth fixtures or DB overrides are
needed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api import legal
from main import app

app.include_router(legal.router)

client = TestClient(app)


def test_compliance_endpoint_requires_no_authentication() -> None:
    response = client.get("/api/v1/legal/compliance")

    assert response.status_code == 200


def test_compliance_endpoint_ignores_a_garbage_authorization_header() -> None:
    """Stronger than "no auth headers were sent": prove the route doesn't
    just skip auth when absent but actually declares no auth dependency
    at all — an expired/garbage bearer token must not turn into a 401.
    """
    response = client.get(
        "/api/v1/legal/compliance",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 200


def test_compliance_endpoint_returns_avv_tom_subprocessors_and_vvt() -> None:
    response = client.get("/api/v1/legal/compliance")

    body = response.json()

    assert "Auftragsverarbeitungsvertrag" in body["avv"]["title"]
    assert "Massnahmen" in body["tom"]["title"]
    assert len(body["subprocessors"]) >= 8
    assert "ExamCraft" in body["vvt_text"]
    assert "Baden-Württemberg" in body["state_specific_notes"]["heading"] or any(
        "Baden-Württemberg" in p for p in body["state_specific_notes"]["paragraphs"]
    )


def test_avv_pdf_endpoint_returns_a_pdf_without_authentication() -> None:
    response = client.get("/api/v1/legal/avv.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    # Content-Disposition is what actually names the downloaded file —
    # a regression that dropped/renamed it would go unnoticed by the
    # status/content-type/magic-bytes checks above.
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="ExamCraft-AVV.pdf"'
    )


def test_tom_pdf_endpoint_returns_a_pdf_without_authentication() -> None:
    response = client.get("/api/v1/legal/tom.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="ExamCraft-TOM.pdf"'
    )


def test_avv_pdf_endpoint_returns_500_when_pdf_rendering_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pins the actual failure behaviour if reportlab ever raises (e.g. a
    future content edit reportlab can't lay out): no try/except wraps the
    export call in ``api.legal``, so FastAPI's default handling applies —
    a generic 500, not a silent/corrupt response.

    Uses a dedicated client with ``raise_server_exceptions=False`` (unlike
    the shared ``client`` above) so the unhandled exception surfaces as an
    HTTP response instead of propagating into the test itself — that's
    what a real client sees.
    """

    def _boom(_document: object) -> bytes:
        raise RuntimeError("reportlab exploded")

    monkeypatch.setattr(legal.AvvPdfExporter, "export", staticmethod(_boom))

    non_raising_client = TestClient(app, raise_server_exceptions=False)
    response = non_raising_client.get("/api/v1/legal/avv.pdf")

    assert response.status_code == 500
