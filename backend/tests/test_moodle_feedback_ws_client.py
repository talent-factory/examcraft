"""TF-435: Moodle WS client helper."""

import httpx
import pytest

from services.moodle_feedback import ws_client
from services.moodle_feedback.ws_client import flatten_moodle_params


def _patch_client(monkeypatch, *, raise_status=None, post_exc=None, json_value=None):
    """Install a fake httpx.Client whose response behaviour we control."""

    class _Resp:
        def raise_for_status(self):
            if raise_status is not None:
                raise raise_status

        def json(self):
            if isinstance(json_value, Exception):
                raise json_value
            return json_value

    class _Client:
        def __init__(self, *a, **k): ...

        def __enter__(self):
            return self

        def __exit__(self, *a): ...

        def post(self, *a, **k):
            if post_exc is not None:
                raise post_exc
            return _Resp()

    monkeypatch.setattr(ws_client.httpx, "Client", _Client)


def test_flatten_nested_list_of_dicts():
    out = flatten_moodle_params(
        {
            "quizid": 7,
            "students": [
                {
                    "useridentifier": "a@x.com",
                    "questions": [
                        {"slot": 1, "mark": 2.0, "comment": "ok", "commentformat": 1}
                    ],
                },
            ],
        }
    )
    assert out["quizid"] == 7
    assert out["students[0][useridentifier]"] == "a@x.com"
    assert out["students[0][questions][0][slot]"] == 1
    assert out["students[0][questions][0][mark]"] == 2.0
    assert out["students[0][questions][0][comment]"] == "ok"
    assert out["students[0][questions][0][commentformat]"] == 1


def test_call_moodle_raises_on_exception_envelope(monkeypatch):
    class _Resp:
        def raise_for_status(self): ...

        def json(self):
            return {"exception": "x", "errorcode": "invalidtoken", "message": "bad"}

    class _Client:
        def __init__(self, *a, **k): ...

        def __enter__(self):
            return self

        def __exit__(self, *a): ...

        def post(self, *a, **k):
            return _Resp()

    monkeypatch.setattr(ws_client.httpx, "Client", _Client)
    with pytest.raises(ws_client.MoodleWsError):
        ws_client.call_moodle("https://m", "tok", "core_x", {})


def test_call_moodle_wraps_non_2xx_as_ws_error(monkeypatch):
    """A non-2xx response (raise_for_status) becomes MoodleWsError, not httpx."""
    _patch_client(
        monkeypatch,
        raise_status=httpx.HTTPStatusError(
            "500",
            request=httpx.Request("POST", "https://m"),
            response=httpx.Response(500),
        ),
    )
    with pytest.raises(ws_client.MoodleWsError):
        ws_client.call_moodle("https://m", "tok", "core_x", {})


def test_call_moodle_wraps_network_error_as_ws_error(monkeypatch):
    """A transport-level failure (e.g. connection refused) becomes MoodleWsError."""
    _patch_client(monkeypatch, post_exc=httpx.ConnectError("refused"))
    with pytest.raises(ws_client.MoodleWsError):
        ws_client.call_moodle("https://m", "tok", "core_x", {})


def test_call_moodle_wraps_non_json_body_as_ws_error(monkeypatch):
    """A 200 with a non-JSON body (proxy/WAF HTML) becomes MoodleWsError."""
    _patch_client(monkeypatch, json_value=ValueError("Expecting value"))
    with pytest.raises(ws_client.MoodleWsError):
        ws_client.call_moodle("https://m", "tok", "core_x", {})
