"""Stored profile picture (EXAMCRAFT-168): normalisation, IdP sync, upload API."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from services import avatar_service
from services.avatar_service import (
    AVATAR_SIZE,
    InvalidAvatarImage,
    normalize_avatar_image,
    sync_idp_avatar,
)


def _png(size=(600, 300), color=(200, 30, 30)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _user(**kw):
    u = MagicMock()
    u.id = 1
    u.avatar_source = kw.get("source")
    u.avatar_url = kw.get("url")
    u.avatar_data = kw.get("data")
    return u


class TestNormalize:
    def test_crops_to_square_png(self):
        out = normalize_avatar_image(_png())
        img = Image.open(BytesIO(out))
        assert img.format == "PNG"
        assert img.size == (AVATAR_SIZE, AVATAR_SIZE)

    def test_strips_exif(self):
        buf = BytesIO()
        exif = Image.Exif()
        exif[0x010F] = "SecretCamera"
        Image.new("RGB", (50, 50)).save(buf, format="JPEG", exif=exif)
        out = normalize_avatar_image(buf.getvalue())
        assert not Image.open(BytesIO(out)).getexif()

    def test_rejects_non_image(self):
        with pytest.raises(InvalidAvatarImage):
            normalize_avatar_image(b"<svg onload=alert(1)/>")


class TestNormalizeLimits:
    def test_rejects_too_many_pixels_before_decoding(self, monkeypatch):
        monkeypatch.setattr(avatar_service, "AVATAR_MAX_PIXELS", 100)
        with pytest.raises(InvalidAvatarImage):
            normalize_avatar_image(_png(size=(20, 20)))

    def test_rejects_unsupported_format(self):
        buf = BytesIO()
        Image.new("RGB", (10, 10)).save(buf, format="BMP")
        with pytest.raises(InvalidAvatarImage):
            normalize_avatar_image(buf.getvalue())

    def test_rejects_truncated_file(self):
        with pytest.raises(InvalidAvatarImage):
            normalize_avatar_image(_png()[:60])


class TestFetch:
    @pytest.fixture(autouse=True)
    def _allow_test_host(self, monkeypatch):
        monkeypatch.setenv("AVATAR_ALLOWED_HOSTS", "idp.example")
        monkeypatch.setattr(
            avatar_service, "_resolve_public_ip", lambda host, port: "93.184.216.34"
        )

    def _client(self, response=None, exc=None):
        client = MagicMock()
        stream = MagicMock()
        if exc:
            client.stream.side_effect = exc
        else:
            stream.__enter__.return_value = response
        client.stream.return_value = stream
        cm = MagicMock()
        cm.__enter__.return_value = client
        return cm, client

    def test_non_image_content_type_is_refused(self):
        resp = MagicMock()
        resp.headers = {"content-type": "text/html"}
        resp.url.host = "idp.example"
        cm, _ = self._client(resp)
        with patch.object(avatar_service.httpx, "Client", return_value=cm):
            assert avatar_service._fetch_idp_picture("https://idp.example/p") is None

    def test_oversized_download_is_refused(self, monkeypatch):
        monkeypatch.setattr(avatar_service, "AVATAR_MAX_DOWNLOAD_BYTES", 10)
        resp = MagicMock()
        resp.headers = {"content-type": "image/png"}
        resp.iter_bytes.return_value = [b"x" * 6, b"x" * 6]
        cm, _ = self._client(resp)
        with patch.object(avatar_service.httpx, "Client", return_value=cm):
            assert avatar_service._fetch_idp_picture("https://idp.example/p") is None

    def test_redirects_are_not_followed(self):
        resp = MagicMock()
        resp.headers = {"content-type": "image/png"}
        resp.iter_bytes.return_value = [b"ok"]
        cm, _ = self._client(resp)
        with patch.object(avatar_service.httpx, "Client", return_value=cm) as c:
            assert avatar_service._fetch_idp_picture("https://idp.example/p") == b"ok"
        assert c.call_args.kwargs["follow_redirects"] is False

    def test_http_error_returns_none(self):
        cm, _ = self._client(exc=avatar_service.httpx.ConnectError("down"))
        with patch.object(avatar_service.httpx, "Client", return_value=cm):
            assert avatar_service._fetch_idp_picture("https://idp.example/p") is None


class TestSync:
    def test_legacy_user_with_same_url_but_no_data_is_synced(self):
        user = _user(url="https://idp/p.png", data=None)
        with patch.object(avatar_service, "_fetch_idp_picture", return_value=_png()):
            assert sync_idp_avatar(MagicMock(), user, "https://idp/p.png") is True

    def test_changed_url_triggers_resync(self):
        user = _user(url="https://idp/old.png", data=b"x", source="idp")
        with patch.object(avatar_service, "_fetch_idp_picture", return_value=_png()):
            assert sync_idp_avatar(MagicMock(), user, "https://idp/new.png") is True
        assert user.avatar_url == "https://idp/new.png"

    def test_skips_uploaded_avatar(self):
        user = _user(source="upload")
        with patch.object(avatar_service, "_fetch_idp_picture") as fetch:
            assert sync_idp_avatar(MagicMock(), user, "https://idp/p.png") is False
        fetch.assert_not_called()

    def test_skips_without_claim(self):
        assert sync_idp_avatar(MagicMock(), _user(), None) is False

    def test_skips_unchanged_url(self):
        user = _user(url="https://idp/p.png", data=b"x", source="idp")
        with patch.object(avatar_service, "_fetch_idp_picture") as fetch:
            assert sync_idp_avatar(MagicMock(), user, "https://idp/p.png") is False
        fetch.assert_not_called()

    def test_stores_picture_and_url(self):
        user, db = _user(), MagicMock()
        with patch.object(avatar_service, "_fetch_idp_picture", return_value=_png()):
            assert sync_idp_avatar(db, user, "https://idp/p.png") is True
        assert user.avatar_source == "idp"
        assert user.avatar_url == "https://idp/p.png"
        assert user.avatar_content_type == "image/png"
        db.commit.assert_called_once()

    def test_download_failure_does_not_raise(self):
        with patch.object(avatar_service, "_fetch_idp_picture", return_value=None):
            assert sync_idp_avatar(MagicMock(), _user(), "https://idp/p.png") is False

    def test_invalid_image_does_not_raise(self):
        db = MagicMock()
        with patch.object(avatar_service, "_fetch_idp_picture", return_value=b"nope"):
            assert sync_idp_avatar(db, _user(), "https://idp/p.png") is False
        db.rollback.assert_called_once()

    def test_http_url_is_refused(self):
        with patch.object(avatar_service.httpx, "Client") as client:
            assert avatar_service._fetch_idp_picture("http://idp/p.png") is None
        client.assert_not_called()


# ---------------------------------------------------------------------------
# API: GET /avatar/{id}, POST/DELETE /me/avatar
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient  # noqa: E402

from database import get_db  # noqa: E402
from main import app  # noqa: E402
from models.auth import Institution, User, UserStatus  # noqa: E402
from utils.auth_utils import get_current_active_user  # noqa: E402


@pytest.fixture
def api(test_db):
    inst = Institution(
        name="Avatar Storage Uni",
        slug="avatar-storage-uni",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(inst)
    test_db.commit()
    user = User(
        email="stored@avatar-storage-uni.ch",
        first_name="S",
        last_name="U",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
        avatar_url="https://idp.example/p.png",
        avatar_source="idp",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    def _db():
        yield test_db

    from api.auth import router as auth_router

    if not any(getattr(r, "path", "") == "/api/auth/me/avatar" for r in app.routes):
        app.include_router(auth_router)
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_active_user] = lambda: user
    yield TestClient(app), user
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_active_user, None)


def test_upload_replaces_idp_picture_and_is_served(api):
    client, user = api
    resp = client.post(
        "/api/auth/me/avatar", files={"file": ("a.png", _png(), "image/png")}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["avatar_source"] == "upload"
    served = client.get(f"/api/auth/avatar/{user.id}")
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert Image.open(BytesIO(served.content)).size == (AVATAR_SIZE, AVATAR_SIZE)


def test_upload_rejects_non_image(api):
    client, _ = api
    resp = client.post(
        "/api/auth/me/avatar", files={"file": ("a.png", b"not an image", "image/png")}
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "auth_avatar_invalid_image"


def test_upload_rejects_oversized(api):
    client, _ = api
    big = b"\x89PNG" + b"0" * (avatar_service.AVATAR_MAX_UPLOAD_BYTES + 10)
    resp = client.post(
        "/api/auth/me/avatar", files={"file": ("a.png", big, "image/png")}
    )
    assert resp.status_code == 413
    assert resp.json()["error_code"] == "auth_avatar_too_large"


def test_delete_clears_stored_picture(api):
    client, user = api
    client.post("/api/auth/me/avatar", files={"file": ("a.png", _png(), "image/png")})
    resp = client.delete("/api/auth/me/avatar")
    assert resp.status_code == 200
    assert resp.json()["avatar_source"] is None
    assert user.avatar_data is None


def test_get_requires_authentication(test_db):
    from api.auth import router as auth_router

    if not any(getattr(r, "path", "") == "/api/auth/me/avatar" for r in app.routes):
        app.include_router(auth_router)
    app.dependency_overrides.pop(get_current_active_user, None)
    client = TestClient(app)
    assert client.get("/api/auth/avatar/1").status_code in (401, 403)


def test_delete_then_get_falls_back_to_404_without_url(api):
    client, user = api
    user.avatar_url = None
    client.post("/api/auth/me/avatar", files={"file": ("a.png", _png(), "image/png")})
    client.delete("/api/auth/me/avatar")
    assert client.get(f"/api/auth/avatar/{user.id}").status_code == 404


class TestSsrfHardening:
    """Internal and non-allowlisted targets are never requested."""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch):
        monkeypatch.delenv("OIDC_ISSUER", raising=False)
        monkeypatch.setenv("AVATAR_ALLOWED_HOSTS", "idp.example")

    def _never_requested(self, url):
        with patch.object(avatar_service.httpx, "Client") as client:
            assert avatar_service._fetch_idp_picture(url) is None
        client.assert_not_called()

    @pytest.mark.parametrize(
        "url",
        [
            "https://evil.example/p.png",
            "https://idp.example.evil.example/p.png",
            "https://notidp.example/p.png",
            "https://127.0.0.1/p.png",
            "https://localhost/p.png",
            "https://169.254.169.254/latest/meta-data",
            "https://user:pw@idp.example/p.png",
            "ftp://idp.example/p.png",
        ],
    )
    def test_disallowed_urls_are_never_fetched(self, url):
        self._never_requested(url)

    @pytest.mark.parametrize(
        "ip",
        [
            "127.0.0.1",
            "10.1.2.3",
            "172.16.0.5",
            "192.168.1.1",
            "169.254.169.254",
            "0.0.0.0",
            "224.0.0.1",
            "240.0.0.1",
            "::1",
            "fe80::1",
            "fc00::1",
            "::ffff:127.0.0.1",
        ],
    )
    def test_allowed_host_resolving_to_internal_ip_is_refused(self, ip, monkeypatch):
        import socket

        monkeypatch.setattr(
            socket, "getaddrinfo", lambda host, port, **kw: [(2, 1, 6, "", (ip, port))]
        )
        self._never_requested("https://idp.example/p.png")

    def test_one_internal_address_among_public_ones_refuses(self, monkeypatch):
        import socket

        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda host, port, **kw: [
                (2, 1, 6, "", ("93.184.216.34", port)),
                (2, 1, 6, "", ("10.0.0.1", port)),
            ],
        )
        self._never_requested("https://idp.example/p.png")

    def test_allowlist_accepts_exact_and_dotted_suffix_only(self):
        assert avatar_service._host_allowed("idp.example")
        assert avatar_service._host_allowed("lh3.idp.example")
        assert not avatar_service._host_allowed("evilidp.example")
        assert avatar_service._host_allowed("lh3.googleusercontent.com")

    def test_trailing_dot_and_case_are_normalised(self, monkeypatch):
        import socket

        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda host, port, **kw: [(2, 1, 6, "", ("93.184.216.34", port))],
        )
        resp = MagicMock()
        resp.headers = {"content-type": "image/png"}
        resp.iter_bytes.return_value = [b"ok"]
        stream = MagicMock()
        stream.__enter__.return_value = resp
        client = MagicMock()
        client.stream.return_value = stream
        cm = MagicMock()
        cm.__enter__.return_value = client
        with patch.object(avatar_service.httpx, "Client", return_value=cm):
            out = avatar_service._fetch_idp_picture("https://IDP.Example./p.png?x=1")
        assert out == b"ok"

    def test_connection_is_pinned_to_checked_ip(self, monkeypatch):
        import socket

        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda host, port, **kw: [(2, 1, 6, "", ("93.184.216.34", port))],
        )
        resp = MagicMock()
        resp.headers = {"content-type": "image/png"}
        resp.iter_bytes.return_value = [b"ok"]
        stream = MagicMock()
        stream.__enter__.return_value = resp
        client = MagicMock()
        client.stream.return_value = stream
        cm = MagicMock()
        cm.__enter__.return_value = client
        with patch.object(avatar_service.httpx, "Client", return_value=cm):
            avatar_service._fetch_idp_picture("https://idp.example/p.png?x=1")
        args, kwargs = client.stream.call_args
        assert args[1] == "https://93.184.216.34/p.png?x=1"
        assert kwargs["headers"]["Host"] == "idp.example"
        assert kwargs["extensions"]["sni_hostname"] == "idp.example"

    def test_issuer_host_is_allowed(self, monkeypatch):
        monkeypatch.setenv("OIDC_ISSUER", "https://login.example.ch/")
        assert avatar_service._host_allowed("login.example.ch")


def _other_user(db, institution_id, email):
    other = User(
        email=email,
        first_name="O",
        last_name="U",
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    other.avatar_data = _png()
    other.avatar_content_type = "image/png"
    other.avatar_source = "upload"
    db.add(other)
    db.commit()
    db.refresh(other)
    return other


def test_colleague_in_same_institution_may_view(api, test_db):
    client, user = api
    colleague = _other_user(test_db, user.institution_id, "col@avatar-storage-uni.ch")
    assert client.get(f"/api/auth/avatar/{colleague.id}").status_code == 200


def test_other_institution_gets_404_like_unknown_id(api, test_db):
    client, user = api
    foreign_inst = Institution(
        name="Foreign Uni",
        slug="avatar-foreign-uni",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(foreign_inst)
    test_db.commit()
    foreign = _other_user(test_db, foreign_inst.id, "f@avatar-foreign-uni.ch")
    denied = client.get(f"/api/auth/avatar/{foreign.id}")
    unknown = client.get("/api/auth/avatar/999999999")
    assert denied.status_code == unknown.status_code == 404
    assert denied.json()["error_code"] == unknown.json()["error_code"]


def test_superuser_may_view_other_institution(api, test_db):
    client, user = api
    foreign_inst = Institution(
        name="Foreign Uni 2",
        slug="avatar-foreign-uni-2",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(foreign_inst)
    test_db.commit()
    foreign = _other_user(test_db, foreign_inst.id, "f2@avatar-foreign-uni.ch")
    user.is_superuser = True
    assert client.get(f"/api/auth/avatar/{foreign.id}").status_code == 200


def test_patch_me_ignores_avatar_url(api):
    """avatar_url is the sync marker only; users cannot set it (SSRF)."""
    client, user = api
    before = user.avatar_url
    resp = client.patch(
        "/api/auth/me", json={"avatar_url": "http://127.0.0.1/x", "bio": "hi"}
    )
    assert resp.status_code == 200, resp.text
    assert user.avatar_url == before
    assert user.bio == "hi"
