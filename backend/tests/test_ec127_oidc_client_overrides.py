"""EXAMCRAFT-127: ``oidc_client`` kann einen zweiten OIDC-Client desselben Issuers
bedienen (MCP-Server). Geprüft wird die echte Verdrahtung gegen einen
gemockten IdP, nicht ein Mock der Funktionen selbst."""

import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt
from jose.exceptions import JWTError

from services import oidc_client

ISSUER = "https://tessera.example"
WEB = "examcraft-web"
MCP = "examcraft-mcp"


@pytest.fixture(autouse=True)
def oidc_env(monkeypatch):
    monkeypatch.setenv("OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("OIDC_CLIENT_ID", WEB)
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "web-secret")  # pragma: allowlist secret
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://testserver/api/v1/auth/callback")
    oidc_client.clear_caches()
    yield
    oidc_client.clear_caches()


@pytest.fixture(scope="module")
def signing_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = jwk.construct(key.public_key(), "RS256").to_dict()
    public.update({"kid": "k1", "use": "sig", "alg": "RS256"})
    return pem.decode(), public


def _mock_discovery(public):
    respx.get(f"{ISSUER}/.well-known/openid-configuration").mock(
        return_value=httpx.Response(
            200,
            json={
                "authorization_endpoint": f"{ISSUER}/oauth/v2/authorize",
                "token_endpoint": f"{ISSUER}/oauth/v2/token",
                "jwks_uri": f"{ISSUER}/oauth/v2/keys",
            },
        )
    )
    respx.get(f"{ISSUER}/oauth/v2/keys").mock(
        return_value=httpx.Response(200, json={"keys": [public]})
    )


def _id_token(signing_key, aud):
    pem, _ = signing_key
    claims = {
        "iss": ISSUER,
        "aud": aud,
        "sub": "sub-1",
        "exp": int(time.time()) + 300,
        "iat": int(time.time()),
        "nonce": "n-1",
    }
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "k1"})


@respx.mock
def test_authorize_url_nutzt_override(signing_key):
    _mock_discovery(signing_key[1])

    url = oidc_client.build_authorize_url(
        "st",
        "ch",
        "n-1",
        client_id_override=MCP,
        redirect_uri_override="https://api.example/mcp/oauth/callback",
    )

    query = parse_qs(urlparse(url).query)
    assert query["client_id"] == [MCP]
    assert query["redirect_uri"] == ["https://api.example/mcp/oauth/callback"]


@respx.mock
def test_authorize_url_default_bleibt_web_client(signing_key):
    _mock_discovery(signing_key[1])

    query = parse_qs(urlparse(oidc_client.build_authorize_url("st", "ch", "n-1")).query)

    assert query["client_id"] == [WEB]
    assert query["redirect_uri"] == ["http://testserver/api/v1/auth/callback"]


@respx.mock
def test_exchange_code_sendet_mcp_credentials(signing_key):
    _mock_discovery(signing_key[1])
    route = respx.post(f"{ISSUER}/oauth/v2/token").mock(
        return_value=httpx.Response(200, json={"id_token": "x"})
    )

    oidc_client.exchange_code(
        "zc",
        "verifier",
        client_id_override=MCP,
        client_secret_override="mcp-secret",  # pragma: allowlist secret
        redirect_uri_override="https://api.example/mcp/oauth/callback",
    )

    request = route.calls.last.request
    assert request.headers["authorization"].startswith("Basic ")
    import base64

    decoded = base64.b64decode(request.headers["authorization"][6:]).decode()
    assert decoded == f"{MCP}:mcp-secret"
    body = parse_qs(request.content.decode())
    assert body["redirect_uri"] == ["https://api.example/mcp/oauth/callback"]
    assert body["code_verifier"] == ["verifier"]


@respx.mock
def test_exchange_code_default_nutzt_web_client(signing_key):
    _mock_discovery(signing_key[1])
    route = respx.post(f"{ISSUER}/oauth/v2/token").mock(
        return_value=httpx.Response(200, json={"id_token": "x"})
    )

    oidc_client.exchange_code("zc", "verifier")

    import base64

    header = route.calls.last.request.headers["authorization"]
    assert base64.b64decode(header[6:]).decode() == f"{WEB}:web-secret"


@respx.mock
def test_validate_id_token_prueft_audience_des_override(signing_key):
    _mock_discovery(signing_key[1])

    claims = oidc_client.validate_id_token(
        _id_token(signing_key, MCP), "n-1", client_id_override=MCP
    )
    assert claims["sub"] == "sub-1"

    # Ein für den Web-Client ausgestelltes Token gilt nicht für den MCP-Client …
    with pytest.raises(JWTError):
        oidc_client.validate_id_token(
            _id_token(signing_key, WEB), "n-1", client_id_override=MCP
        )
    # … und umgekehrt gilt ein MCP-Token nicht beim Web-Login (Default).
    with pytest.raises(JWTError):
        oidc_client.validate_id_token(_id_token(signing_key, MCP), "n-1")


@respx.mock
def test_discovery_ohne_pflichtfelder_ist_ein_idp_fehler():
    respx.get(f"{ISSUER}/.well-known/openid-configuration").mock(
        return_value=httpx.Response(200, json={"authorization_endpoint": f"{ISSUER}/a"})
    )

    with pytest.raises(httpx.DecodingError, match="token_endpoint"):
        oidc_client.build_authorize_url("s", "c", "n")


@respx.mock
@pytest.mark.parametrize("bad", [None, ""])
def test_discovery_mit_leerem_pflichtfeld_ist_ein_idp_fehler(bad):
    respx.get(f"{ISSUER}/.well-known/openid-configuration").mock(
        return_value=httpx.Response(
            200,
            json={
                "authorization_endpoint": f"{ISSUER}/a",
                "token_endpoint": f"{ISSUER}/t",
                "jwks_uri": bad,
            },
        )
    )

    with pytest.raises(httpx.DecodingError, match="jwks_uri"):
        oidc_client.build_authorize_url("s", "c", "n")


@respx.mock
def test_leerer_client_id_override_faellt_nicht_auf_web_client_zurueck(signing_key):
    _mock_discovery(signing_key[1])

    url = oidc_client.build_authorize_url("s", "c", "n", client_id_override="")

    assert parse_qs(urlparse(url).query, keep_blank_values=True)["client_id"] == [""]
