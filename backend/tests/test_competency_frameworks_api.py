"""API tests for competency framework CRUD (TF-400)."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from main import app
from database import get_db
from utils.auth_utils import get_current_user, get_current_active_user


@pytest.fixture
def seeded_user(test_db):
    from models.auth import Institution, User

    inst = Institution(
        name="API HKP Inst",
        slug="api-hkp-inst",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    user = User(
        email="dozent@example.com",
        first_name="Doz",
        last_name="Ent",
        institution_id=inst.id,
        status="active",
        password_hash="dummy_hash",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    test_db.refresh(inst)
    return user, inst


def _make_client(test_db, user_id, institution_id, *, is_creator=True):
    """Return a TestClient bound to a mock user.

    ``is_creator`` only affects the ``has_permission`` semantics:
    - True  → has "create_questions" but NOT "manage_settings" (non-admin owner)
    - False → same permissions but different id so the I1 guard fires
    The permission-aware lambda is always used so ``manage_settings`` returns False.
    """
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.institution_id = institution_id
    mock_user.is_superuser = False
    mock_user.has_permission = lambda perm: perm == "create_questions"

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def api_client(test_db, seeded_user):
    """Original fixture: owner user, always-True has_permission (admin-like for
    the original 4 tests that rely on being both owner and admin)."""
    user, _ = seeded_user
    real_user = MagicMock()
    real_user.id = user.id
    real_user.institution_id = user.institution_id
    real_user.is_superuser = False
    real_user.has_permission = lambda *_a, **_k: True

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: real_user
    app.dependency_overrides[get_current_active_user] = lambda: real_user
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def _payload():
    return {
        "name": "Modul B – Wirkungsvoll kommunizieren",
        "module_code": "B",
        "description": "HKB",
        "rendered_text": "# HKB\n### B1 ...",
        "language": "de",
        "visibility": "institution",
        "competencies": [
            {
                "code": "B1",
                "title": "adressatengerecht kommunizieren",
                "descriptors": [{"text": "Sie setzen Modelle ein.", "ln_level": 2}],
                "position": 1,
            }
        ],
    }


def test_create_then_get(api_client):
    r = api_client.post("/api/v1/competency-frameworks", json=_payload())
    assert r.status_code == 201, r.text
    fw_id = r.json()["id"]
    assert r.json()["module_code"] == "B"
    assert r.json()["competencies"][0]["code"] == "B1"

    r2 = api_client.get(f"/api/v1/competency-frameworks/{fw_id}")
    assert r2.status_code == 200
    assert r2.json()["rendered_text"].startswith("# HKB")


def test_list_scoped_to_institution(api_client):
    api_client.post("/api/v1/competency-frameworks", json=_payload())
    r = api_client.get("/api/v1/competency-frameworks")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_update_rendered_text(api_client):
    fw_id = api_client.post("/api/v1/competency-frameworks", json=_payload()).json()[
        "id"
    ]
    r = api_client.put(
        f"/api/v1/competency-frameworks/{fw_id}",
        json={"rendered_text": "# HKB v2"},
    )
    assert r.status_code == 200
    assert r.json()["rendered_text"] == "# HKB v2"


def test_archive_hides_from_default_list(api_client):
    fw_id = api_client.post("/api/v1/competency-frameworks", json=_payload()).json()[
        "id"
    ]
    assert (
        api_client.post(f"/api/v1/competency-frameworks/{fw_id}/archive").status_code
        == 200
    )
    assert len(api_client.get("/api/v1/competency-frameworks").json()) == 0
    assert (
        len(
            api_client.get("/api/v1/competency-frameworks?include_archived=true").json()
        )
        == 1
    )


# ---------------------------------------------------------------------------
# New security / edge-case tests (code-review fixes)
# ---------------------------------------------------------------------------


def test_get_nonexistent_returns_404(test_db, seeded_user):
    """GET on a non-existent framework id must return 404."""
    user, _ = seeded_user
    client = _make_client(test_db, user.id, user.institution_id)
    try:
        r = client.get("/api/v1/competency-frameworks/999999")
        assert r.status_code == 404, r.text
    finally:
        app.dependency_overrides.clear()


def test_non_owner_same_institution_cannot_update(test_db, seeded_user):
    """A non-admin user who is NOT the creator of a framework gets 403 on PUT.

    Enforces Fix I1: the owner-or-admin guard in _get_for_write.
    """
    owner, inst = seeded_user

    # Create the framework as the owner (user A)
    owner_client = _make_client(test_db, owner.id, owner.institution_id)
    r = owner_client.post("/api/v1/competency-frameworks", json=_payload())
    assert r.status_code == 201, r.text
    fw_id = r.json()["id"]
    app.dependency_overrides.clear()

    # Create a second user (user B) in the SAME institution
    from models.auth import User

    user_b = User(
        email="other@example.com",
        first_name="Other",
        last_name="User",
        institution_id=inst.id,
        status="active",
        password_hash="dummy_hash",
    )
    test_db.add(user_b)
    test_db.commit()
    test_db.refresh(user_b)

    # user B tries to PUT → must be 403 (sees the framework via visibility=institution,
    # but is not the creator and not an admin)
    other_client = _make_client(test_db, user_b.id, user_b.institution_id)
    try:
        r2 = other_client.put(
            f"/api/v1/competency-frameworks/{fw_id}",
            json={"rendered_text": "# tampered"},
        )
        assert r2.status_code == 403, r2.text
    finally:
        app.dependency_overrides.clear()


def test_cross_institution_isolation(test_db, seeded_user):
    """A user from a different institution cannot see or mutate another institution's framework."""
    owner, inst = seeded_user

    # Create the framework as the owner (institution 1)
    owner_client = _make_client(test_db, owner.id, owner.institution_id)
    r = owner_client.post("/api/v1/competency-frameworks", json=_payload())
    assert r.status_code == 201, r.text
    fw_id = r.json()["id"]
    app.dependency_overrides.clear()

    # Create a second institution and a user in it
    from models.auth import Institution, User

    inst2 = Institution(
        name="Other Inst",
        slug="other-inst",
        subscription_tier="free",
        max_users=5,
        max_documents=20,
        max_questions_per_month=100,
    )
    test_db.add(inst2)
    test_db.flush()
    user_c = User(
        email="foreign@example.com",
        first_name="Foreign",
        last_name="User",
        institution_id=inst2.id,
        status="active",
        password_hash="dummy_hash",
    )
    test_db.add(user_c)
    test_db.commit()
    test_db.refresh(user_c)
    test_db.refresh(inst2)

    foreign_client = _make_client(test_db, user_c.id, user_c.institution_id)
    try:
        # GET → 404 (not in _visible_query for inst2)
        r_get = foreign_client.get(f"/api/v1/competency-frameworks/{fw_id}")
        assert r_get.status_code == 404, r_get.text

        # PUT → 404 (same isolation: _get_for_write uses _visible_query first)
        r_put = foreign_client.put(
            f"/api/v1/competency-frameworks/{fw_id}",
            json={"rendered_text": "# injected"},
        )
        assert r_put.status_code == 404, r_put.text
    finally:
        app.dependency_overrides.clear()


_RENDERED_WITH_HK = (
    "# HKB\n\n## Handlungskompetenz\n\n"
    "### B1 adressatengerecht kommunizieren\n\n"
    "- Sie setzen Modelle ein. (LN 2)\n"
    "- Sie vereinfachen Fachbegriffe. (LN 1)\n\n"
    "### B2 die eigene Meinung vertreten\n\n"
    "- Sie argumentieren überzeugend. (LN 3)\n"
)


def test_create_derives_competencies_from_rendered_text(api_client):
    """TF-400: without explicit competencies, HKs are parsed from rendered_text."""
    payload = {
        "name": "Modul B – via rendered_text",
        "module_code": "B",
        "rendered_text": _RENDERED_WITH_HK,
        "language": "de",
        "visibility": "institution",
        # deliberately NO competencies field → derivation kicks in
    }
    r = api_client.post("/api/v1/competency-frameworks", json=payload)
    assert r.status_code == 201, r.text
    competencies = r.json()["competencies"]
    assert [c["code"] for c in competencies] == ["B1", "B2"]
    b1 = competencies[0]
    assert b1["title"] == "adressatengerecht kommunizieren"
    assert b1["descriptors"][0] == {"text": "Sie setzen Modelle ein.", "ln_level": 2}


def test_update_rendered_text_syncs_competencies(api_client):
    """TF-400: when rendered_text changes, the HKs are re-derived (upsert)."""
    fw_id = api_client.post(
        "/api/v1/competency-frameworks",
        json={
            "name": "Modul B – leer",
            "module_code": "B",
            "rendered_text": "# HKB ohne HKs",
            "language": "de",
            "visibility": "institution",
        },
    ).json()["id"]
    # Initially no HKs (rendered_text has no ### B<n> headings)
    assert (
        api_client.get(f"/api/v1/competency-frameworks/{fw_id}").json()["competencies"]
        == []
    )

    r = api_client.put(
        f"/api/v1/competency-frameworks/{fw_id}",
        json={"rendered_text": _RENDERED_WITH_HK},
    )
    assert r.status_code == 200, r.text
    codes = [c["code"] for c in r.json()["competencies"]]
    assert codes == ["B1", "B2"]


def test_framework_out_exposes_created_by(api_client):
    """FrameworkOut returns created_by so the frontend can check ownership."""
    created = api_client.post("/api/v1/competency-frameworks", json=_payload()).json()
    assert "created_by" in created
    assert created["created_by"] is not None

    fetched = api_client.get(f"/api/v1/competency-frameworks/{created['id']}").json()
    assert fetched["created_by"] == created["created_by"]


# ---------------------------------------------------------------------------
# Duplicate-code handling (no bare 500) + retention + private visibility
# ---------------------------------------------------------------------------

_RENDERED_DUPLICATE_HEADINGS = (
    "# HKB\n\n"
    "### B1 erste Fassung\n\n- Kriterium A. (LN 2)\n\n"
    "### B1 zweite Fassung, gleicher Code\n\n- Kriterium B. (LN 1)\n"
)


def test_create_with_duplicate_headings_dedupes_not_500(api_client):
    """Duplicate ### B1 headings in rendered_text must not produce a 500
    (IntegrityError on ux_competencies_framework_code) — the code is
    deduplicated (first version wins)."""
    payload = {
        "name": "Modul mit Dublette",
        "rendered_text": _RENDERED_DUPLICATE_HEADINGS,
        "language": "de",
        "visibility": "institution",
    }
    r = api_client.post("/api/v1/competency-frameworks", json=payload)
    assert r.status_code == 201, r.text
    assert [c["code"] for c in r.json()["competencies"]] == ["B1"]


def test_create_with_malformed_competency_code_returns_422(api_client):
    """CompetencyIn.code must match the parser format ^[A-Za-z]\\d+$
    (tagging contract); a deviating code is rejected with 422."""
    payload = _payload()
    payload["competencies"] = [
        {"code": "nicht ok", "title": "x", "descriptors": [], "position": 1}
    ]
    r = api_client.post("/api/v1/competency-frameworks", json=payload)
    assert r.status_code == 422, r.text


def test_create_with_explicit_duplicate_codes_returns_400(api_client):
    """Two explicit competencies with the same code are a client error →
    400 with the code in the message, not a bare 500."""
    payload = _payload()
    payload["competencies"] = [
        {"code": "B1", "title": "erste", "descriptors": [], "position": 1},
        {"code": "B1", "title": "zweite", "descriptors": [], "position": 2},
    ]
    r = api_client.post("/api/v1/competency-frameworks", json=payload)
    assert r.status_code == 400, r.text
    assert "B1" in r.json()["detail"]


def test_update_retains_removed_competency_code(api_client):
    """_sync_competencies_from_text keeps codes that are no longer present in
    rendered_text (otherwise SET NULL on question_reviews.competency_id), and
    still updates existing codes in-place."""
    fw_id = api_client.post(
        "/api/v1/competency-frameworks",
        json={
            "name": "Modul Retention",
            "rendered_text": _RENDERED_WITH_HK,  # B1 + B2
            "language": "de",
            "visibility": "institution",
        },
    ).json()["id"]

    # Update: only B1 remains, with a changed title; B2 is missing from the new text.
    r = api_client.put(
        f"/api/v1/competency-frameworks/{fw_id}",
        json={"rendered_text": "# HKB\n\n### B1 neuer Titel\n\n- Kriterium. (LN 2)\n"},
    )
    assert r.status_code == 200, r.text
    by_code = {c["code"]: c for c in r.json()["competencies"]}
    assert set(by_code) == {"B1", "B2"}  # B2 retained (FK-safe)
    assert by_code["B1"]["title"] == "neuer Titel"  # B1 updated in-place


def test_private_framework_visible_to_creator_only(test_db, seeded_user):
    """A private framework is visible to its creator, but not to other users
    of the same institution (visibility='private')."""
    owner, inst = seeded_user
    owner_client = _make_client(test_db, owner.id, owner.institution_id)
    payload = _payload()
    payload["visibility"] = "private"
    r = owner_client.post("/api/v1/competency-frameworks", json=payload)
    assert r.status_code == 201, r.text
    fw_id = r.json()["id"]
    assert owner_client.get(f"/api/v1/competency-frameworks/{fw_id}").status_code == 200
    app.dependency_overrides.clear()

    from models.auth import User

    peer = User(
        email="peer@example.com",
        first_name="Peer",
        last_name="User",
        institution_id=inst.id,
        status="active",
        password_hash="dummy_hash",
    )
    test_db.add(peer)
    test_db.commit()
    test_db.refresh(peer)

    peer_client = _make_client(test_db, peer.id, peer.institution_id)
    try:
        assert (
            peer_client.get(f"/api/v1/competency-frameworks/{fw_id}").status_code == 404
        )
        assert all(
            f["id"] != fw_id
            for f in peer_client.get("/api/v1/competency-frameworks").json()
        )
    finally:
        app.dependency_overrides.clear()
