"""Tests for CORS `expose_headers` wiring (TF-782 review follow-up).

`ComposerService.downloadExport` reads `X-Export-Skipped-Positions` from the
cross-origin export response via axios (`response.headers[...]`), which the
browser only exposes to JS if the backend lists it in
`Access-Control-Expose-Headers`. Every existing test mocks axios directly, so
none of them would catch a typo/removal of that entry breaking the feature in
production while staying green locally. A pure wiring check without DB/
lifespan — fast and CI-safe, mirrors test_gzip_middleware.py's pattern.
"""

from fastapi.middleware.cors import CORSMiddleware

from main import app


def _cors_entry():
    entries = [m for m in app.user_middleware if m.cls is CORSMiddleware]
    assert entries, "CORSMiddleware ist nicht in der App registriert"
    return entries[0]


def test_export_skipped_positions_header_is_cors_exposed():
    mw = _cors_entry()
    kwargs = getattr(mw, "kwargs", None) or getattr(mw, "options", {})
    assert "X-Export-Skipped-Positions" in kwargs.get("expose_headers", [])


def test_content_disposition_header_is_still_cors_exposed():
    """Regression guard: adding the new header must not have replaced the
    existing Content-Disposition entry that every other export/download
    already relies on."""
    mw = _cors_entry()
    kwargs = getattr(mw, "kwargs", None) or getattr(mw, "options", {})
    assert "Content-Disposition" in kwargs.get("expose_headers", [])
