"""Fehler-Envelope in eingehängten Unter-Apps (TF-773 PR 2b, ADR 0006).

Exception-Handler überqueren ``app.mount()`` nicht: eine eingehängte
FastAPI-App hat ihre eigene ExceptionMiddleware und rendert ein
``AppHTTPException`` mit Starlettes Standard-Handler — ``error_code`` fällt
still weg. Betroffen ist die MCP-Unter-App (``premium/backend/mcp``), deren
OAuth-Endpunkte seit PR 2b codierte Fehler werfen.

Ohne Datenbank: geprüft wird nur die Verdrahtung der Handler, nicht ein
fachlicher Endpunkt.
"""

from __future__ import annotations

import ast
import pathlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from errors import AppHTTPException
from main import install_error_envelope_handlers


def _mounted(sub_app: FastAPI) -> TestClient:
    parent = FastAPI()
    parent.mount("/sub", sub_app)
    return TestClient(parent)


def _sub_app_raising_coded_error() -> FastAPI:
    sub_app = FastAPI()

    @sub_app.get("/boom")
    def boom():
        raise AppHTTPException(
            400,
            "Probe",
            error_code="mcp_auth_probe",
            error_params={"client_id": "abc"},
        )

    return sub_app


def test_ohne_installation_geht_der_code_verloren():
    """Belegt die Voraussetzung. Wird dieser Test rot, reichen Handler
    inzwischen über den Mount — dann ist ``install_error_envelope_handlers``
    überflüssig und kann entfallen."""
    response = _mounted(_sub_app_raising_coded_error()).get("/sub/boom")

    assert response.status_code == 400
    assert response.json() == {"detail": "Probe"}


def test_installierte_handler_liefern_das_envelope():
    sub_app = _sub_app_raising_coded_error()
    install_error_envelope_handlers(sub_app)

    response = _mounted(sub_app).get("/sub/boom")

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Probe",
        "error_code": "mcp_auth_probe",
        "error_params": {"client_id": "abc"},
    }


def test_validierungsfehler_der_unter_app_tragen_den_reservierten_code():
    sub_app = FastAPI()

    @sub_app.get("/items")
    def items(limit: int):
        return {"limit": limit}

    install_error_envelope_handlers(sub_app)

    response = _mounted(sub_app).get("/sub/items?limit=abc")

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


def test_main_installiert_die_handler_auf_der_mcp_app():
    """Die MCP-App wird nur im Full-Deployment in der Lifespan eingehängt —
    ein HTTP-Test käme ohne den ganzen Premium-Stack nicht dorthin. Deshalb
    wird die Aufrufstelle statisch gehalten: fällt der Aufruf beim Umbau weg,
    verliert ``mcp/auth.py`` seine Codes, ohne dass ein anderer Test es merkt.
    """
    source = pathlib.Path(__file__).resolve().parents[1] / "main.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            getattr(node.func, "id", None) == "install_error_envelope_handlers"
            or (
                getattr(node.func, "attr", None) == "mount"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "/mcp"
            )
        )
    ]
    install = [
        c
        for c in calls
        if getattr(c.func, "id", None) == "install_error_envelope_handlers"
    ]
    mount = [c for c in calls if getattr(c.func, "attr", None) == "mount"]

    assert len(mount) == 1, "app.mount('/mcp', …) nicht (eindeutig) gefunden"
    assert any(
        isinstance(c.args[0], ast.Name) and c.args[0].id == mount[0].args[1].id
        for c in install
    ), "install_error_envelope_handlers() wird nicht auf der MCP-App aufgerufen"
