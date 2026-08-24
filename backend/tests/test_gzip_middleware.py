"""Tests for GZip response compression (TF-378).

Verifies that `GZipMiddleware` is registered in the app and configured with
a `minimum_size`, so small responses stay uncompressed (no overhead). A pure
wiring check without DB/lifespan — fast and CI-safe.
"""

from fastapi.middleware.gzip import GZipMiddleware

from main import app


def _gzip_entries():
    return [m for m in app.user_middleware if m.cls is GZipMiddleware]


def test_gzip_middleware_is_registered():
    assert _gzip_entries(), "GZipMiddleware ist nicht in der App registriert"


def test_gzip_minimum_size_configured():
    mw = _gzip_entries()[0]
    # Depending on version, Starlette stores middleware arguments in .kwargs
    # or .options — cover both paths.
    kwargs = getattr(mw, "kwargs", None) or getattr(mw, "options", {})
    assert kwargs.get("minimum_size") == 1000


def test_gzip_added_inside_cors():
    """CORS must remain the outermost layer (header on all responses).

    In Starlette, the last middleware added becomes the outermost layer,
    i.e. CORS must come before GZip in the list.
    """
    from fastapi.middleware.cors import CORSMiddleware

    classes = [m.cls for m in app.user_middleware]
    assert CORSMiddleware in classes and GZipMiddleware in classes
    assert classes.index(CORSMiddleware) < classes.index(GZipMiddleware), (
        "CORS muss nach GZip hinzugefügt werden (äusserste Schicht bleiben)"
    )
