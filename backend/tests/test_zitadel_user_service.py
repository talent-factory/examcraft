"""Tests für services.zitadel_user_service (EXAMCRAFT-128)."""

import httpx
import pytest
import respx

from services.zitadel_user_service import (
    ZitadelError,
    ZitadelTransientError,
    delete_zitadel_user,
    fetch_zitadel_profile,
)

ISSUER = "https://login.test"
NOT_FOUND = {"code": 5, "message": "User not found"}


@pytest.fixture(autouse=True)
def _zitadel_env(monkeypatch):
    monkeypatch.setenv("ZITADEL_ISSUER", ISSUER)
    monkeypatch.setenv("ZITADEL_USER_DELETE_CLIENT_ID", "cid")
    monkeypatch.setenv(
        "ZITADEL_USER_DELETE_CLIENT_SECRET", "csecret"
    )  # pragma: allowlist secret


def _token(mock):
    return mock.post(f"{ISSUER}/oauth/v2/token").respond(
        200, json={"access_token": "tok"}
    )


@respx.mock
def test_delete_returns_true_and_sends_bearer():
    _token(respx)
    route = respx.delete(f"{ISSUER}/v2/users/sub1").respond(200, json={})

    assert delete_zitadel_user("sub1") is True
    assert route.calls.last.request.headers["authorization"] == "Bearer tok"


@respx.mock
def test_delete_is_idempotent_on_404():
    _token(respx)
    respx.delete(f"{ISSUER}/v2/users/sub1").respond(404, json=NOT_FOUND)

    assert delete_zitadel_user("sub1") is False


@respx.mock
@pytest.mark.parametrize("status", [500, 503, 429])
def test_delete_server_errors_are_transient(status):
    _token(respx)
    respx.delete(f"{ISSUER}/v2/users/sub1").respond(status)

    with pytest.raises(ZitadelTransientError):
        delete_zitadel_user("sub1")


@respx.mock
def test_delete_forbidden_is_permanent_error():
    _token(respx)
    respx.delete(f"{ISSUER}/v2/users/sub1").respond(403)

    with pytest.raises(ZitadelError):
        delete_zitadel_user("sub1")


@respx.mock
def test_network_error_is_transient():
    respx.post(f"{ISSUER}/oauth/v2/token").mock(side_effect=httpx.ConnectError("down"))

    with pytest.raises(ZitadelTransientError):
        delete_zitadel_user("sub1")


@respx.mock
def test_token_rejection_is_permanent_error():
    respx.post(f"{ISSUER}/oauth/v2/token").respond(401)

    with pytest.raises(ZitadelError):
        delete_zitadel_user("sub1")


def test_missing_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("ZITADEL_ISSUER")

    with pytest.raises(ZitadelError):
        delete_zitadel_user("sub1")


@respx.mock
def test_fetch_profile_returns_user_object():
    _token(respx)
    respx.get(f"{ISSUER}/v2/users/sub1").respond(
        200, json={"user": {"userId": "sub1", "human": {"email": {"email": "a@b.ch"}}}}
    )

    assert fetch_zitadel_profile("sub1")["userId"] == "sub1"


@respx.mock
def test_fetch_profile_none_when_absent():
    _token(respx)
    respx.get(f"{ISSUER}/v2/users/sub1").respond(404, json=NOT_FOUND)

    assert fetch_zitadel_profile("sub1") is None


@respx.mock
def test_non_json_token_response_is_transient():
    respx.post(f"{ISSUER}/oauth/v2/token").respond(200, text="<html>Wartung</html>")

    with pytest.raises(ZitadelTransientError):
        delete_zitadel_user("sub1")


@respx.mock
def test_network_error_on_delete_is_transient():
    _token(respx)
    respx.delete(f"{ISSUER}/v2/users/sub1").mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(ZitadelTransientError):
        delete_zitadel_user("sub1")


@respx.mock
def test_sub_is_url_encoded():
    _token(respx)
    route = respx.delete(f"{ISSUER}/v2/users/a%2Fb").respond(200, json={})

    assert delete_zitadel_user("a/b") is True
    assert route.called


@respx.mock
def test_fetch_profile_without_user_key_fails():
    _token(respx)
    respx.get(f"{ISSUER}/v2/users/sub1").respond(200, json={"other": 1})

    with pytest.raises(ZitadelError):
        fetch_zitadel_profile("sub1")


def test_incomplete_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("ZITADEL_USER_DELETE_CLIENT_SECRET")

    with pytest.raises(ZitadelError):
        delete_zitadel_user("sub1")


def test_zitadel_error_is_not_a_runtime_error():
    assert not issubclass(ZitadelError, RuntimeError)


@respx.mock
def test_404_without_not_found_body_is_error_not_success():
    _token(respx)
    respx.delete(f"{ISSUER}/v2/users/sub1").respond(404, text="<html>nginx</html>")

    with pytest.raises(ZitadelError):
        delete_zitadel_user("sub1")


# --- Konfigurations-Health-Check (EXAMCRAFT-134) ---------------------------


@pytest.fixture
def _no_health_cache(monkeypatch):
    import services.zitadel_user_service as svc

    monkeypatch.setattr(svc, "_health_cache", None)


@respx.mock
def test_config_check_ok_only_fetches_token(_no_health_cache):
    from services.zitadel_user_service import check_zitadel_user_delete_config

    token = _token(respx)
    assert check_zitadel_user_delete_config() == "ok"
    assert token.called
    assert len(respx.calls) == 1  # keine User-API


@pytest.mark.parametrize(
    ("var", "value"),
    [
        ("ZITADEL_ISSUER", None),
        ("ZITADEL_USER_DELETE_CLIENT_ID", None),
        ("ZITADEL_USER_DELETE_CLIENT_SECRET", None),
        ("ZITADEL_USER_DELETE_CLIENT_SECRET", "   "),
    ],
)
def test_config_check_not_configured(monkeypatch, _no_health_cache, var, value):
    from services.zitadel_user_service import check_zitadel_user_delete_config

    if value is None:
        monkeypatch.delenv(var)
    else:
        monkeypatch.setenv(var, value)
    assert check_zitadel_user_delete_config() == "not_configured"


@respx.mock
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (httpx.Response(401), "auth_rejected"),
        (httpx.Response(403), "auth_rejected"),
        (httpx.Response(404), "error"),
        (httpx.Response(400), "error"),
        (httpx.Response(200, json={}), "error"),
        (httpx.Response(200, text="<html>"), "unreachable"),
        (httpx.Response(500), "unreachable"),
        (httpx.Response(429), "unreachable"),
    ],
)
def test_config_check_token_response_classification(
    _no_health_cache, response, expected
):
    from services.zitadel_user_service import check_zitadel_user_delete_config

    respx.post(f"{ISSUER}/oauth/v2/token").mock(return_value=response)
    assert check_zitadel_user_delete_config() == expected


@respx.mock
def test_config_check_network_error_is_unreachable(_no_health_cache):
    from services.zitadel_user_service import check_zitadel_user_delete_config

    respx.post(f"{ISSUER}/oauth/v2/token").mock(side_effect=httpx.ConnectError("x"))
    assert check_zitadel_user_delete_config() == "unreachable"


def test_config_check_never_raises_on_unexpected_error(monkeypatch, _no_health_cache):
    import services.zitadel_user_service as svc

    def boom(*_args):
        raise ValueError("unerwartet")

    monkeypatch.setattr(svc, "_access_token", boom)
    assert svc.check_zitadel_user_delete_config() == "error"


@respx.mock
def test_config_check_cache_hit_and_error_is_cached(_no_health_cache):
    from services.zitadel_user_service import check_zitadel_user_delete_config

    token = respx.post(f"{ISSUER}/oauth/v2/token").respond(401)
    assert check_zitadel_user_delete_config(use_cache=True) == "auth_rejected"
    assert check_zitadel_user_delete_config(use_cache=True) == "auth_rejected"
    assert token.call_count == 1


@respx.mock
def test_config_check_cache_expires_after_ttl(monkeypatch, _no_health_cache):
    import services.zitadel_user_service as svc

    clock = [1000.0]
    monkeypatch.setattr(svc.time, "monotonic", lambda: clock[0])
    token = _token(respx)

    svc.check_zitadel_user_delete_config(use_cache=True)
    clock[0] += svc._HEALTH_CACHE_TTL_SECONDS + 1
    svc.check_zitadel_user_delete_config(use_cache=True)
    assert token.call_count == 2


@respx.mock
def test_config_check_without_cache_neither_reads_nor_writes(_no_health_cache):
    import services.zitadel_user_service as svc

    token = _token(respx)
    svc.check_zitadel_user_delete_config()
    svc.check_zitadel_user_delete_config()
    assert token.call_count == 2
    assert svc._health_cache is None


def test_config_check_invalid_issuer_is_error_not_unreachable(
    monkeypatch, _no_health_cache
):
    from services.zitadel_user_service import check_zitadel_user_delete_config

    monkeypatch.setenv("ZITADEL_ISSUER", "login.test")  # ohne Schema
    assert check_zitadel_user_delete_config() == "error"
