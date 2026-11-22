"""Tests für scripts.zitadel_bulk_import (EXAMCRAFT-130)."""

import json
import os
import stat
import uuid

import bcrypt
import httpx
import pytest

from models.auth import Institution, OAuthAccount, User
from scripts import zitadel_bulk_import as zbi


def _hash(cost: int = 12) -> str:
    return bcrypt.hashpw(b"pw", bcrypt.gensalt(rounds=cost)).decode()


@pytest.fixture
def institution(test_db):
    slug = f"zbi-{uuid.uuid4().hex[:8]}"
    inst = Institution(
        name=slug,
        slug=slug,
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    return inst


def _user(db, inst, tag, **kw):
    user = User(
        email=f"{tag}-{uuid.uuid4().hex[:6]}@example.test",
        first_name="Vor",
        last_name="Nach",
        institution_id=inst.id,
        status=kw.pop("status", "active"),
        **kw,
    )
    db.add(user)
    db.flush()
    return user


def _only(db, inst):
    """Fremde Benutzer der geteilten CI-DB für den Export ausblenden (pending).

    Der Export liest alle Benutzer. Ohne das scheitern ``main``-Tests an Zeilen
    anderer Tests (Hash, Duplikat, OAuth); die Änderung wird zurückgerollt.
    """
    for other in db.query(User).filter(User.institution_id != inst.id).all():
        other.status = "pending"
    db.flush()


def _entries(doc):
    return {e["userId"]: e["user"] for e in doc["dataOrgs"]["orgs"][0]["humanUsers"]}


def test_export_rules(test_db, institution):
    pw = _user(
        test_db,
        institution,
        "pw",
        password_hash=_hash(),
        is_email_verified=True,
        preferred_language="fr",
    )
    unverified = _user(test_db, institution, "unv", password_hash=_hash())
    pending = _user(
        test_db, institution, "pend", status="pending", password_hash=_hash()
    )
    inactive = _user(
        test_db, institution, "inact", status="inactive", password_hash=_hash()
    )
    oauth = _user(test_db, institution, "oa")
    test_db.add(
        OAuthAccount(user_id=oauth.id, provider="google", provider_user_id="g-1")
    )
    nothing = _user(test_db, institution, "none")
    test_db.flush()

    doc, report = zbi.build_import_data(test_db, "org-1", {"google": "idp-g"})
    users = _entries(doc)

    assert doc["dataOrgs"]["orgs"][0]["orgId"] == "org-1"
    assert f"examcraft-{pending.id}" not in users
    assert pending.id in report.skipped_pending

    p = users[f"examcraft-{pw.id}"]
    assert p["hashedPassword"]["algorithm"] == "bcrypt"
    assert p["profile"]["preferredLanguage"] == "fr"
    assert p["email"]["isEmailVerified"] is True
    assert p["passwordChangeRequired"] is False

    u = users[f"examcraft-{unverified.id}"]
    assert u["email"]["isEmailVerified"] is False
    assert u["profile"]["preferredLanguage"] == "de"

    assert inactive.id in report.to_deactivate
    o = users[f"examcraft-{oauth.id}"]
    assert "hashedPassword" not in o
    assert o[zbi.IDP_LINKS_FIELD] == [
        {
            zbi.IDP_ID_KEY: "idp-g",
            zbi.IDP_EXTERNAL_ID_KEY: "g-1",
            "displayName": oauth.email,
        }
    ]
    assert nothing.id in report.without_credentials
    assert pw.id not in report.without_credentials
    assert pw.id not in report.unsupported_hash


def test_unmapped_provider_and_bad_hash(test_db, institution):
    low = _user(test_db, institution, "low", password_hash=_hash(cost=5))
    gh = _user(test_db, institution, "gh")
    test_db.add(OAuthAccount(user_id=gh.id, provider="github", provider_user_id="x"))
    test_db.flush()

    doc, report = zbi.build_import_data(test_db, "org-1", {})

    assert low.id in report.unsupported_hash
    assert report.unmapped_providers.get("github", 0) >= 1
    assert "hashedPassword" not in _entries(doc)[f"examcraft-{low.id}"]
    assert gh.id in report.lost_oauth_links
    assert gh.id in report.without_credentials


def test_write_private_file_mode_and_no_overwrite(tmp_path):
    target = tmp_path / "import.json"
    zbi.write_private_file(str(target), {"a": 1})
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600
    assert json.loads(target.read_text()) == {"a": 1}
    with pytest.raises(FileExistsError):
        zbi.write_private_file(str(target), {"a": 2})


def test_link_subs(test_db, institution):
    fresh = _user(test_db, institution, "fresh")
    done = _user(test_db, institution, "done", zitadel_sub="s-done")
    clash = _user(test_db, institution, "clash", zitadel_sub="s-old")
    gone = _user(test_db, institution, "gone")
    off = _user(test_db, institution, "off", status="suspended")
    _user(test_db, institution, "pend", status="pending")
    mapping = {
        fresh.email.upper(): "s-fresh",
        done.email: "s-done",
        clash.email: "s-new",
        off.email: "s-off",
    }
    mapping = {k.lower(): v for k, v in mapping.items()}

    report = zbi.link_subs(test_db, mapping)

    assert fresh.zitadel_sub == "s-fresh"
    assert clash.zitadel_sub == "s-old"
    assert clash.id in report.conflicts
    assert done.id in report.already_linked
    assert gone.id in report.unmatched
    assert (off.id, "s-off") in report.to_deactivate
    assert not report.ok


def test_fetch_subs_paginates(monkeypatch):
    monkeypatch.setenv("ZITADEL_ISSUER", "https://z.test")
    monkeypatch.setenv("ZITADEL_ORG_ID", "org-1")
    monkeypatch.setenv("ZITADEL_IMPORT_TOKEN", "t")
    pages = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        pages.append(body["query"]["offset"])
        n = zbi._PAGE_SIZE if body["query"]["offset"] == 0 else 1
        return httpx.Response(
            200,
            json={
                "result": [
                    {
                        "userId": f"u{body['query']['offset']}-{i}",
                        "human": {
                            "email": {"email": f"A{i}-{body['query']['offset']}@X.test"}
                        },
                    }
                    for i in range(n)
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    subs = zbi.fetch_subs(client)
    assert pages == [0, zbi._PAGE_SIZE]
    assert len(subs) == zbi._PAGE_SIZE + 1
    assert "a0-0@x.test" in subs


def test_post_import_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("ZITADEL_ISSUER", "https://z.test")
    monkeypatch.setenv("ZITADEL_ORG_ID", "org-1")
    monkeypatch.setenv("ZITADEL_IMPORT_TOKEN", "t")
    f = tmp_path / "i.json"
    f.write_text("{}")
    ok = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))
    )
    zbi.post_import(str(f), ok)
    partial = httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"errors": [{"x": 1}]})
        )
    )
    with pytest.raises(zbi.ImportError_):
        zbi.post_import(str(f), partial)
    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403)))
    with pytest.raises(zbi.ImportError_, match="403"):
        zbi.post_import(str(f), bad)


def test_settings_require_env(monkeypatch):
    for k in ("ZITADEL_ISSUER", "ZITADEL_ORG_ID", "ZITADEL_IMPORT_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(zbi.ImportError_):
        zbi._settings()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("$2b$12$" + "a" * 53, True),
        ("$2a$10$" + "a" * 53, True),
        ("$2y$16$" + "a" * 53, True),
        ("$2b$09$" + "a" * 53, False),
        ("$2b$17$" + "a" * 53, False),
        ("$2x$12$" + "a" * 53, False),
        ("$2b$xx$" + "a" * 53, False),
        ("$2b$12$short", False),
        ("$argon2id$v=19$m=65536,t=3,p=4$" + "a" * 29, False),
    ],
)
def test_is_bcrypt(value, expected):
    assert len(value) == 60 or not expected
    assert zbi._is_bcrypt(value) is expected


def _env(monkeypatch):
    monkeypatch.setenv("ZITADEL_ISSUER", "https://z.test")
    monkeypatch.setenv("ZITADEL_ORG_ID", "org-1")
    monkeypatch.setenv("ZITADEL_IMPORT_TOKEN", "t")


def _client(status, text="{}"):
    return httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(status, text=text))
    )


def _deactivate_client(post_status, state=None, get_status=200):
    """POST .../deactivate liefert ``post_status``, GET den Benutzerzustand."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                post_status, json={"message": "Benutzer ist bereits inaktiv"}
            )
        return httpx.Response(get_status, json={"user": {"state": state}})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_deactivate_idempotent_only_when_user_is_inactive(monkeypatch):
    _env(monkeypatch)
    zbi.deactivate_in_zitadel("s1", _deactivate_client(200))
    # Fehlertext ist übersetzt/versionsabhängig: entscheidend ist der Zustand.
    for status in (400, 412):
        zbi.deactivate_in_zitadel(
            "s1", _deactivate_client(status, "USER_STATE_INACTIVE")
        )
    # Aktiv trotz Fehler, Zustand nicht lesbar oder anderer Status: Fehler.
    for client in (
        _deactivate_client(400, "USER_STATE_ACTIVE"),
        _deactivate_client(412, "USER_STATE_INACTIVE", get_status=500),
        _deactivate_client(403, "USER_STATE_INACTIVE"),
        _deactivate_client(404, "USER_STATE_INACTIVE"),
        _deactivate_client(500, "USER_STATE_INACTIVE"),
    ):
        with pytest.raises(zbi.ImportError_):
            zbi.deactivate_in_zitadel("s1", client)


def _failing_client(exc):
    def handler(request):
        raise exc

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_network_errors_become_import_errors(monkeypatch, tmp_path):
    _env(monkeypatch)
    boom = httpx.ConnectError("boom")
    with pytest.raises(zbi.ImportError_, match="ConnectError"):
        zbi.deactivate_in_zitadel("s1", _failing_client(boom))
    with pytest.raises(zbi.ImportError_, match="ConnectError"):
        zbi.fetch_subs(_failing_client(boom))
    with pytest.raises(zbi.ImportError_, match="HTTP 500"):
        zbi.fetch_subs(_client(500))
    with pytest.raises(zbi.ImportError_, match="Antwortformat"):
        zbi.fetch_subs(_client(200, '{"result": ["kein-dict"]}'))


def test_post_import_unknown_state_hint(monkeypatch, tmp_path):
    _env(monkeypatch)
    f = tmp_path / "i.json"
    f.write_text("{}")
    with pytest.raises(zbi.ImportError_, match="nicht blind wiederholen"):
        zbi.post_import(str(f), _failing_client(httpx.ReadTimeout("slow")))
    with pytest.raises(zbi.ImportError_, match="nicht blind wiederholen"):
        zbi.post_import(str(f), _client(504))
    with pytest.raises(zbi.ImportError_, match="Antwortformat"):
        zbi.post_import(str(f), _client(200, "[]"))


def test_post_import_error_message_has_ids_but_no_body(monkeypatch, tmp_path):
    _env(monkeypatch)
    f = tmp_path / "i.json"
    f.write_text("{}")
    body = json.dumps(
        {"errors": [{"type": "human", "userId": "examcraft-7", "message": "a@b.test"}]}
    )
    with pytest.raises(zbi.ImportError_) as info:
        zbi.post_import(str(f), _client(200, body))
    assert "examcraft-7" in str(info.value)
    assert "a@b.test" not in str(info.value)


def _recording_client(response):
    """Client, der den gesendeten JSON-Body in ``sent`` ablegt."""
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return response

    return httpx.Client(transport=httpx.MockTransport(handler)), sent


def test_post_import_sends_server_timeout(monkeypatch, tmp_path):
    # Ohne ``timeout`` antwortet Zitadel mit HTTP 500 ("invalid duration").
    _env(monkeypatch)
    f = tmp_path / "i.json"
    f.write_text(json.dumps({"dataOrgs": {"orgs": []}}))
    client, sent = _recording_client(httpx.Response(200, json={}))
    zbi.post_import(str(f), client)
    assert sent[0]["timeout"] == zbi._IMPORT_SERVER_TIMEOUT
    assert sent[0]["dataOrgs"] == {"orgs": []}


def test_post_import_keeps_timeout_from_file(monkeypatch, tmp_path):
    _env(monkeypatch)
    f = tmp_path / "i.json"
    f.write_text(json.dumps({"timeout": "5m", "dataOrgs": {"orgs": []}}))
    client, sent = _recording_client(httpx.Response(200, json={}))
    zbi.post_import(str(f), client)
    assert sent[0]["timeout"] == "5m"


ORG_EXISTS = {
    "type": "org",
    "id": "org-1",
    "message": "ID=ORG-lapo2n Message=Errors.Org.AlreadyExisting",
}


def test_post_import_ignores_existing_org_error(monkeypatch, tmp_path):
    # Die Org existiert immer schon; Zitadel importiert die Benutzer trotzdem.
    _env(monkeypatch)
    f = tmp_path / "i.json"
    f.write_text("{}")
    body = json.dumps({"errors": [ORG_EXISTS], "success": {"orgs": [{"orgId": "o"}]}})
    zbi.post_import(str(f), _client(200, body))


def test_post_import_reports_user_errors_next_to_existing_org(monkeypatch, tmp_path):
    _env(monkeypatch)
    f = tmp_path / "i.json"
    f.write_text("{}")
    user_error = {
        "type": "human_user",
        "id": "examcraft-1",
        "message": "ID=V3-DKcYh Message=Errors.User.ExternalIDP.AlreadyExists",
    }
    body = json.dumps({"errors": [ORG_EXISTS, user_error]})
    with pytest.raises(zbi.ImportError_) as info:
        zbi.post_import(str(f), _client(200, body))
    text = str(info.value)
    assert "1 Fehler" in text
    assert "examcraft-1 (Errors.User.ExternalIDP.AlreadyExists)" in text


def test_post_import_org_error_of_other_kind_is_not_ignored(monkeypatch, tmp_path):
    _env(monkeypatch)
    f = tmp_path / "i.json"
    f.write_text("{}")
    other = {"type": "org", "id": "org-1", "message": "Errors.Org.NotFound"}
    with pytest.raises(zbi.ImportError_, match="1 Fehler"):
        zbi.post_import(str(f), _client(200, json.dumps({"errors": [other]})))


def test_post_import_error_key_never_leaks_free_text(monkeypatch, tmp_path):
    _env(monkeypatch)
    f = tmp_path / "i.json"
    f.write_text("{}")
    leaky = {"type": "human_user", "id": "examcraft-7", "message": "a@b.test"}
    with pytest.raises(zbi.ImportError_) as info:
        zbi.post_import(str(f), _client(200, json.dumps({"errors": [leaky]})))
    assert "examcraft-7 (unbekannt)" in str(info.value)
    assert "a@b.test" not in str(info.value)


def test_post_import_unreadable_body_is_error(monkeypatch, tmp_path):
    _env(monkeypatch)
    f = tmp_path / "i.json"
    f.write_text("{}")
    with pytest.raises(zbi.ImportError_, match="nicht lesbar"):
        zbi.post_import(str(f), _client(200, "not json"))
    with pytest.raises(zbi.ImportError_, match="nicht lesbar"):
        zbi.post_import(str(tmp_path / "missing.json"), _client(200))


def test_fetch_subs_duplicate_email_is_error(monkeypatch):
    _env(monkeypatch)
    body = json.dumps(
        {
            "result": [
                {"userId": "a", "human": {"email": {"email": "x@y.test"}}},
                {"userId": "b", "human": {"email": {"email": "X@y.test"}}},
            ]
        }
    )
    with pytest.raises(zbi.ImportError_, match="doppelte"):
        zbi.fetch_subs(_client(200, body))
    with pytest.raises(zbi.ImportError_, match="Antwortformat"):
        zbi.fetch_subs(_client(200, "{}"))


def test_link_subs_duplicate_local_email_is_conflict(test_db, institution):
    first = _user(test_db, institution, "dup")
    second = _user(test_db, institution, "dup2")
    second.email = first.email.upper()
    test_db.flush()
    report = zbi.link_subs(test_db, {first.email.lower(): "s-1"})
    assert first.id in report.linked
    assert second.id in report.conflicts


def _patch_main(monkeypatch, test_db, subs, deactivated):
    test_db.commit()  # rollback() in main() verwirft sonst die Test-Benutzer
    import database

    monkeypatch.setattr(database, "SessionLocal", lambda: _Session(test_db))
    monkeypatch.setattr(zbi, "fetch_subs", lambda: subs)

    def fake_deactivate(sub):
        if sub == "s-fail":
            raise zbi.ImportError_("Deaktivieren: HTTP 500")
        deactivated.append(sub)

    monkeypatch.setattr(zbi, "deactivate_in_zitadel", fake_deactivate)
    _env(monkeypatch)


class _Session:
    """Reicht die Test-Session durch, ohne sie bei close() zu schliessen."""

    def __init__(self, session):
        self._s = session

    def __getattr__(self, name):
        return getattr(self._s, name)

    def close(self):
        pass


def test_main_link_dry_run_apply_and_abort(monkeypatch, test_db, institution, capsys):
    active = _user(test_db, institution, "act")
    off = _user(test_db, institution, "off", status="inactive")
    subs = {active.email.lower(): "s-act", off.email.lower(): "s-off"}
    deactivated: list[str] = []
    _patch_main(monkeypatch, test_db, subs, deactivated)
    # fremde Zeilen der geteilten DB dürfen den Lauf nicht beeinflussen
    others = [u for u in test_db.query(User).all() if u.id not in (active.id, off.id)]
    for u in others:
        subs.setdefault(u.email.strip().lower(), f"s-other-{u.id}")

    assert zbi.main(["link"]) == 0
    test_db.refresh(active)
    assert active.zitadel_sub is None and deactivated == []

    assert zbi.main(["link", "--apply"]) == 0
    test_db.refresh(active)
    assert active.zitadel_sub == "s-act"
    assert "s-off" in deactivated

    out = capsys.readouterr()
    assert "@" not in out.out + out.err

    # Idempotenter Wiederholungslauf
    assert zbi.main(["link", "--apply"]) == 0


def test_main_link_deactivation_failure_commits_nothing(
    monkeypatch, test_db, institution, capsys
):
    off = _user(test_db, institution, "off", status="suspended")
    subs = {off.email.lower(): "s-fail"}
    for u in test_db.query(User).all():
        subs.setdefault(u.email.strip().lower(), f"s-other-{u.id}")
    _patch_main(monkeypatch, test_db, subs, [])

    assert zbi.main(["link", "--apply"]) == 2
    test_db.refresh(off)
    assert off.zitadel_sub is None
    assert str(off.id) in capsys.readouterr().err


def test_main_link_unmatched_aborts(monkeypatch, test_db, institution):
    user = _user(test_db, institution, "lone")
    _patch_main(monkeypatch, test_db, {}, [])
    assert zbi.main(["link", "--apply"]) == 1
    test_db.refresh(user)
    assert user.zitadel_sub is None


_ALLOW = ["--allow-without-credentials", "--allow-unmapped-idps"]


def test_main_export_blocks_and_allows(
    monkeypatch, test_db, institution, tmp_path, capsys
):
    _user(test_db, institution, "nocred")
    hashed = _user(test_db, institution, "hashed", password_hash=_hash())
    _only(test_db, institution)
    _patch_main(monkeypatch, test_db, {}, [])
    out = tmp_path / "e.json"

    assert zbi.main(["export", "--out", str(out)]) == 1
    assert not out.exists()

    assert zbi.main(["export", "--out", str(out), *_ALLOW]) == 0
    assert stat.S_IMODE(os.stat(out).st_mode) == 0o600
    # Der Hash steht in der Datei, nie in der Ausgabe.
    assert hashed.password_hash in out.read_text()
    captured = capsys.readouterr()
    assert "$2" not in captured.out + captured.err
    assert "@" not in captured.out + captured.err

    # Vorhandene Datei: Exit 2, nur der Typname, Datei unverändert.
    before = out.read_text()
    assert zbi.main(["export", "--out", str(out), *_ALLOW]) == 2
    err = capsys.readouterr().err
    assert "FileExistsError" in err and str(out) not in err
    assert out.read_text() == before


def test_main_export_blocks_unsupported_hash_even_with_flags(
    monkeypatch, test_db, institution, tmp_path
):
    _user(test_db, institution, "low", password_hash=_hash(cost=5))
    _patch_main(monkeypatch, test_db, {}, [])
    out = tmp_path / "e.json"
    assert zbi.main(["export", "--out", str(out), *_ALLOW]) == 1
    assert not out.exists()


def test_export_duplicate_email_is_blocking(test_db, institution):
    first = _user(test_db, institution, "dup", password_hash=_hash())
    second = _user(test_db, institution, "dup2", password_hash=_hash())
    second.email = f" {first.email.upper()} "
    test_db.flush()
    doc, report = zbi.build_import_data(test_db, "org-1")
    assert second.id in report.duplicate_email
    assert f"examcraft-{second.id}" not in _entries(doc)


def test_main_export_blocks_duplicates_and_unmapped_idps(
    monkeypatch, test_db, institution, tmp_path
):
    first = _user(test_db, institution, "dup", password_hash=_hash())
    second = _user(test_db, institution, "dup2", password_hash=_hash())
    second.email = first.email.upper()
    test_db.flush()
    _only(test_db, institution)
    _patch_main(monkeypatch, test_db, {}, [])
    out = tmp_path / "e.json"
    assert zbi.main(["export", "--out", str(out), *_ALLOW]) == 1
    assert not out.exists()

    second.email = f"other-{uuid.uuid4().hex[:6]}@example.test"
    # github ist gültiger Provider, aber (ohne --idp) nicht zugeordnet.
    test_db.add(OAuthAccount(user_id=first.id, provider="github", provider_user_id="x"))
    test_db.commit()
    assert zbi.main(["export", "--out", str(out), "--allow-without-credentials"]) == 1
    assert not out.exists()
    assert zbi.main(["export", "--out", str(out), *_ALLOW]) == 0


def test_write_private_file_removes_partial_file_on_error(tmp_path, monkeypatch):
    target = tmp_path / "import.json"

    def boom(*args, **kwargs):
        raise RuntimeError("disk")

    monkeypatch.setattr(zbi.json, "dump", boom)
    with pytest.raises(RuntimeError):
        zbi.write_private_file(str(target), {"hash": "x"})
    assert not target.exists()


def test_main_link_dry_run_with_findings_exits_1(monkeypatch, test_db, institution):
    user = _user(test_db, institution, "lone")
    _patch_main(monkeypatch, test_db, {}, [])
    assert zbi.main(["link"]) == 1
    test_db.refresh(user)
    assert user.zitadel_sub is None


def test_main_link_mixed_deactivation_rolls_back_but_reports(
    monkeypatch, test_db, institution, capsys
):
    ok = _user(test_db, institution, "ok", status="inactive")
    bad = _user(test_db, institution, "bad", status="suspended")
    subs = {ok.email.lower(): "s-ok", bad.email.lower(): "s-fail"}
    for u in test_db.query(User).all():
        subs.setdefault(u.email.strip().lower(), f"s-other-{u.id}")
    deactivated: list[str] = []
    _patch_main(monkeypatch, test_db, subs, deactivated)

    assert zbi.main(["link", "--apply"]) == 2
    assert (
        "s-ok" in deactivated
    )  # in Zitadel erledigt, bleibt beim Wiederholen idempotent
    test_db.refresh(ok)
    test_db.refresh(bad)
    assert ok.zitadel_sub is None and bad.zitadel_sub is None
    err = capsys.readouterr().err
    assert str(bad.id) in err


def test_main_handles_foreign_errors_with_type_name_only(
    monkeypatch, test_db, institution, capsys
):
    from sqlalchemy.exc import OperationalError

    _user(test_db, institution, "x")
    _patch_main(monkeypatch, test_db, {}, [])

    def boom(db, subs):
        raise OperationalError("SELECT secret-host", {"p": "x@y.test"}, Exception())

    monkeypatch.setattr(zbi, "link_subs", boom)
    assert zbi.main(["link"]) == 2
    err = capsys.readouterr().err
    assert "ImportError_" in err or "sub eintragen fehlgeschlagen" in err
    assert "secret-host" not in err and "x@y.test" not in err


def test_main_link_commit_failure_reports_partial_state(
    monkeypatch, test_db, institution, capsys
):
    from sqlalchemy.exc import IntegrityError

    off = _user(test_db, institution, "off", status="inactive")
    subs = {off.email.lower(): "s-off"}
    for u in test_db.query(User).all():
        subs.setdefault(u.email.strip().lower(), f"s-other-{u.id}")
    deactivated: list[str] = []
    _patch_main(monkeypatch, test_db, subs, deactivated)

    def failing_commit():
        raise IntegrityError("INSERT secret-host", {}, Exception())

    monkeypatch.setattr(test_db, "commit", failing_commit)
    assert zbi.main(["link", "--apply"]) == 2
    err = capsys.readouterr().err
    assert "Teilzustand" in err and str(off.id) in err
    assert "secret-host" not in err
