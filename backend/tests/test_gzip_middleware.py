"""Tests für die GZip-Response-Kompression (TF-378).

Verifiziert, dass `GZipMiddleware` in der App registriert ist und mit einem
`minimum_size` konfiguriert wurde, damit kleine Responses unkomprimiert
bleiben (kein Overhead). Reiner Wiring-Check ohne DB/Lifespan — schnell und
CI-sicher.
"""

from fastapi.middleware.gzip import GZipMiddleware

from main import app


def _gzip_entries():
    return [m for m in app.user_middleware if m.cls is GZipMiddleware]


def test_gzip_middleware_is_registered():
    assert _gzip_entries(), "GZipMiddleware ist nicht in der App registriert"


def test_gzip_minimum_size_configured():
    mw = _gzip_entries()[0]
    # Starlette legt die Middleware-Argumente je nach Version in .kwargs oder
    # .options ab — beide Pfade abdecken.
    kwargs = getattr(mw, "kwargs", None) or getattr(mw, "options", {})
    assert kwargs.get("minimum_size") == 1000


def test_gzip_added_inside_cors():
    """CORS muss äusserste Schicht bleiben (Header auf allen Responses).

    In Starlette wird zuletzt hinzugefügte Middleware zur äussersten Schicht,
    d.h. CORS muss in der Liste vor GZip stehen.
    """
    from fastapi.middleware.cors import CORSMiddleware

    classes = [m.cls for m in app.user_middleware]
    assert CORSMiddleware in classes and GZipMiddleware in classes
    assert classes.index(CORSMiddleware) < classes.index(GZipMiddleware), (
        "CORS muss nach GZip hinzugefügt werden (äusserste Schicht bleiben)"
    )
