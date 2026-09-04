"""Test that the WebSocket route is registered correctly"""

from starlette.routing import WebSocketRoute


def test_websocket_route_registered():
    """The /ws/tasks/{task_id} endpoint must be registered as a WebSocketRoute"""
    # Plain import: main.py registers this module under its canonical name
    # (TF-660), so this is the same module object the app serves from. The
    # previous spec_from_file_location("core_api_v1_websocket", ...) built a
    # third, private copy and asserted against that instead.
    from api.v1 import websocket as websocket_api

    # Check that the router is defined
    assert hasattr(websocket_api, "router"), "WebSocket API hat kein router Attribut"
    assert websocket_api.router is not None, "WebSocket router ist None"

    # Check that the WebSocketRoute exists
    ws_routes = [
        r
        for r in websocket_api.router.routes
        if isinstance(r, WebSocketRoute) and "ws/tasks" in r.path
    ]
    assert len(ws_routes) > 0, (
        f"WebSocketRoute /ws/tasks/{{task_id}} nicht gefunden. "
        f"Routes im websocket router: {[(type(r).__name__, getattr(r, 'path', '?')) for r in websocket_api.router.routes]}"
    )
