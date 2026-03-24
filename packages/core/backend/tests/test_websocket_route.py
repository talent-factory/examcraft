"""Test dass WebSocket Route korrekt registriert ist"""

import importlib
import os
from starlette.routing import WebSocketRoute


def test_websocket_route_registered():
    """Der /ws/tasks/{task_id} Endpoint muss als WebSocketRoute registriert sein"""
    # Importiere WebSocket API direkt
    core_api_path = os.path.join(os.path.dirname(__file__), "..", "api")

    spec_ws = importlib.util.spec_from_file_location(
        "core_api_v1_websocket", os.path.join(core_api_path, "v1", "websocket.py")
    )
    websocket_api = importlib.util.module_from_spec(spec_ws)
    spec_ws.loader.exec_module(websocket_api)

    # Prüfe dass der Router definiert ist
    assert hasattr(websocket_api, "router"), "WebSocket API hat kein router Attribut"
    assert websocket_api.router is not None, "WebSocket router ist None"

    # Prüfe dass die WebSocketRoute existiert
    ws_routes = [
        r
        for r in websocket_api.router.routes
        if isinstance(r, WebSocketRoute) and "ws/tasks" in r.path
    ]
    assert len(ws_routes) > 0, (
        f"WebSocketRoute /ws/tasks/{{task_id}} nicht gefunden. "
        f"Routes im websocket router: {[(type(r).__name__, getattr(r, 'path', '?')) for r in websocket_api.router.routes]}"
    )
