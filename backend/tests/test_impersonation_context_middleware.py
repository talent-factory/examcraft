"""Tests for ImpersonationContextMiddleware (TF-741).

Guards against state leaking between requests: contextvars are not
automatically request-isolated (a reused thread/task can see a stale
value from a previous request unless something resets it). The
middleware must reset the value to ``None`` before *and* after every
request regardless of what a route handler did to it.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.impersonation_context import ImpersonationContextMiddleware
from utils.impersonation_context import (
    ImpersonationContext,
    get_impersonation_context,
    set_impersonation_context,
)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ImpersonationContextMiddleware)

    @app.post("/set")
    def set_route():
        set_impersonation_context(
            ImpersonationContext(
                impersonator_id=1, impersonation_session_id=2, token_jti="jti-1"
            )
        )
        ctx = get_impersonation_context()
        return {"seen_within_request": ctx is not None}

    @app.get("/read")
    def read_route():
        ctx = get_impersonation_context()
        return {"impersonating": ctx is not None}

    return app


def test_context_is_none_by_default():
    client = TestClient(_build_app())
    response = client.get("/read")
    assert response.json() == {"impersonating": False}


def test_value_set_within_a_request_is_visible_within_that_same_request():
    client = TestClient(_build_app())
    response = client.post("/set")
    assert response.json() == {"seen_within_request": True}


def test_value_does_not_leak_into_the_next_request():
    client = TestClient(_build_app())

    client.post("/set")  # mutates the context inside its own request
    response = client.get("/read")  # a fresh request right after

    assert response.json() == {"impersonating": False}
