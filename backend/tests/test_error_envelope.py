"""Fehler-Envelope und Locale-Auflösung über HTTP (TF-773 Teil A/E).

Der Contract-Test (test_error_codes_contract.py) prüft statisch, dass jeder
Code einen Schlüssel hat. Hier geht es um das, was ein Client tatsächlich
sieht: Feldform, Rückwärtskompatibilität und welche Sprache gewinnt.

Die Tags-API dient als Messpunkt, weil sie in TF-671 der belegte Schadensfall
war — deutscher Prosatext ohne Code, den das Frontend nur über den
Sonderfall ``errors/apiDetail.ts`` retten konnte.

Abgrenzung zu ``test_translation_service.py``: das prüft ``get_request_locale``
als Einheit gegen Mock-Objekte und deckt dieselben drei Auflösungspfade bereits
ab. Hier laufen sie über HTTP durch Middleware, Dependency und Handler — das
ist die Verdrahtung, nicht die Funktion. Beide Ebenen sind nötig: die
Unit-Tests waren grün, während ``tags.py`` die Locale überhaupt nicht auflöste.
"""

from __future__ import annotations

import itertools
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from models.auth import Institution, User, UserStatus

pytestmark = pytest.mark.usefixtures("test_engine")


# ---------------------------------------------------------------------------
# Fixtures — bewusst eigene, damit dieser Test nicht an den Hilfsfunktionen
# von test_tags_api.py hängt (dort ist der Fokus die Fachlogik, hier das
# Antwortformat).
# ---------------------------------------------------------------------------


#: Präfix für alles, was diese Datei anlegt — die Teardown-Bedingung hängt
#: daran, deshalb an einer Stelle definiert.
_PREFIX = "envelope-"

#: Eigener, hoch liegender ID-Bereich. Zwei Gründe, die IDs explizit zu setzen
#: statt sie der Sequenz zu überlassen:
#:
#: 1. Ein expliziter Wert verbraucht **keinen** Sequenzwert. Andere Dateien
#:    (``test_list_documents_filters.py``: ``id=900``, ``test_exam_api.py``,
#:    ``test_document_tags.py``: ``id=800``) legen Zeilen mit festen IDs an und
#:    kollidieren, sobald die Sequenz bis in deren Bereich gelaufen ist. Weil
#:    diese Datei echte Commits braucht (der TestClient ruft die Endpunkte über
#:    HTTP auf, savepoint-isolierte Zeilen sind für ihn unsichtbar), würde sie
#:    die Sequenz sonst weiterschieben und die Kollision anderswo auslösen —
#:    als 22 Fehler in einer Datei, an der nichts falsch ist.
#: 2. Der Bereich liegt weit über allem, was die Suite sonst fest vergibt.
_ID_BASE = 990_000
_id_counter = itertools.count(_ID_BASE)


@pytest.fixture()
def envelope_db(test_engine):
    """Committende Session mit eigenem Aufräumen.

    Die Endpunkte laufen über einen echten TestClient, die Zeilen müssen also
    *committet* sein — die savepoint-isolierte ``test_db``-Fixture aus
    conftest.py geht dafür nicht. Was committet ist, überlebt aber den Test:
    ohne dieses Teardown quittiert ``test_exam_api.py`` (läuft alphabetisch
    direkt danach) mit ``duplicate key value violates unique constraint
    "institutions_pkey"``.
    """
    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(bind=test_engine)()
    yield session
    try:
        session.rollback()
        session.query(User).filter(User.email.like(f"{_PREFIX}%")).delete(
            synchronize_session=False
        )
        session.query(Institution).filter(Institution.slug.like(f"{_PREFIX}%")).delete(
            synchronize_session=False
        )
        session.commit()
    finally:
        session.close()


def _uid() -> str:
    return uuid.uuid4().hex[:10]


def _institution(db: Session) -> Institution:
    suffix = _uid()
    inst = Institution(
        id=next(_id_counter),
        name=f"Envelope Uni {suffix}",
        slug=f"{_PREFIX}uni-{suffix}",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def _user(db: Session, institution_id: int, preferred_language: str | None) -> User:
    user = User(
        id=next(_id_counter),
        email=f"{_PREFIX}{_uid()}@test.com",
        first_name="Envelope",
        last_name="Tester",
        password_hash="dummy_hash",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        preferred_language=preferred_language,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _client(db: Session, user: User) -> TestClient:
    import api.tags as tags_module
    from database import get_db
    from utils.auth_utils import get_current_active_user

    app.include_router(tags_module.router)

    # Eine echte Generatorfunktion, kein `lambda: iter([db])`: FastAPI
    # entscheidet an der *Funktion* (inspect.isgeneratorfunction), ob es die
    # Dependency als Kontextmanager auflöst. Ein Lambda, das nur einen
    # Iterator zurückgibt, wird durchgereicht — der Endpunkt bekommt dann den
    # Iterator statt der Session.
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Form des Envelopes
# ---------------------------------------------------------------------------


def test_umgestellter_endpunkt_liefert_detail_und_error_code(envelope_db):
    """Der Kernvertrag: ``error_code`` NEBEN ``detail``, nicht darin."""
    inst = _institution(envelope_db)
    user = _user(envelope_db, inst.id, "de")
    client = _client(envelope_db, user)

    response = client.delete("/api/v1/tags/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "tags_not_found"
    # Der ganze Grund für das Geschwisterfeld: 89 Frontend-Stellen lesen
    # detail als String. Wird das je zu einem Objekt, brechen die still.
    assert isinstance(body["detail"], str)
    assert body["detail"] == "Tag nicht gefunden."


def test_error_params_erscheint_nur_bei_interpolation(envelope_db):
    inst = _institution(envelope_db)
    user = _user(envelope_db, inst.id, "de")
    client = _client(envelope_db, user)

    body = client.delete("/api/v1/tags/999999").json()
    assert "error_params" not in body, (
        "Eine Meldung ohne Variablen darf kein leeres error_params-Objekt "
        "auf jede Fehlerantwort legen."
    )


def test_nicht_umgestellter_pfad_bleibt_unveraendert(envelope_db):
    """Die Migration ist additiv — ein Endpunkt ohne Code liefert exakt das
    Format von vorher, ohne ``error_code``-Feld. Ohne diese Zusage müsste
    Teil B ein Stichtag sein statt paketweise laufen zu können.

    Zwei Belege statt einem (TF-773 review): Starlettes eigener Router-404
    (unabhängig davon, wie viele der 619 Stellen bereits migriert sind) UND
    ein echter Business-Endpunkt, den dieses PR nicht angefasst hat
    (``students.py`` gehört zu den verbleibenden 219 Stellen aus Teil B).
    Beide Assertions prüfen Bytegleichheit, nicht nur die Abwesenheit von
    ``error_code`` — sonst würde ein neues drittes Feld unbemerkt
    durchrutschen.
    """
    inst = _institution(envelope_db)
    user = _user(envelope_db, inst.id, "de")
    client = _client(envelope_db, user)

    # 1. Eine Route, die es nicht gibt: Starlettes eigener 404.
    response = client.get("/api/v1/gibt-es-nicht")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

    # 2. Ein echter, unmigrierter Business-Endpunkt.
    import api.students as students_module
    from utils.auth_utils import get_current_user

    if "/api/v1/students/{student_id}" not in [r.path for r in app.routes]:
        app.include_router(students_module.router)
    # require_permission() hängt an get_current_user, nicht an
    # get_current_active_user (_client() überschreibt nur Letzteres), und
    # is_superuser umgeht die RBAC-Prüfung, die nicht Gegenstand dieses
    # Tests ist.
    app.dependency_overrides[get_current_user] = lambda: user
    user.is_superuser = True
    envelope_db.commit()

    response = client.get("/api/v1/students/999999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Studi nicht gefunden"}


def test_401_traegt_www_authenticate_header(envelope_db):
    """TF-773 review: main.py's generischer Handler muss ``headers``
    durchreichen — sonst verliert jeder 401 lautlos ``WWW-Authenticate``,
    obwohl die restliche Suite grün bliebe (kein anderer Test prüft den
    Header). Bewusst OHNE ``get_current_user``-Override: dieser Test
    braucht den echten Token-Ablehnungspfad in
    ``auth_utils.py::get_current_user``, der den Header setzt."""
    import api.tags as tags_module
    from database import get_db

    if "/api/v1/tags/{tag_id}" not in [r.path for r in app.routes]:
        app.include_router(tags_module.router)

    def override_get_db():
        yield envelope_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.delete(
        "/api/v1/tags/999999",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401, response.text
    assert response.json()["error_code"] == "auth_token_invalid"
    assert response.headers["www-authenticate"] == "Bearer"


def test_validierungsfehler_traegt_reservierten_code(envelope_db):
    """422 erzeugt FastAPI selbst. ``detail`` bleibt bewusst die auswertbare
    Fehlerliste — sie durch einen Satz zu ersetzen wäre ein echter Bruch."""
    inst = _institution(envelope_db)
    user = _user(envelope_db, inst.id, "de")
    client = _client(envelope_db, user)

    response = client.post("/api/v1/tags", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert isinstance(body["detail"], list)


# ---------------------------------------------------------------------------
# Locale-Auflösung — ein Test je Pfad (Teil E)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "preferred, accept_language, erwarteter_text",
    [
        # 1. preferred_language gesetzt — gewinnt auch gegen Accept-Language
        ("fr", "de-CH,de;q=0.9", "Tag introuvable."),
        # 2. nur Accept-Language
        (None, "it-CH,it;q=0.9", "Tag non trovato."),
        # 3. keines von beiden -> DEFAULT_LOCALE
        (None, None, "Tag nicht gefunden."),
    ],
    ids=["preferred_language", "accept_language", "default"],
)
def test_aufloesungspfade(envelope_db, preferred, accept_language, erwarteter_text):
    inst = _institution(envelope_db)
    user = _user(envelope_db, inst.id, preferred)
    client = _client(envelope_db, user)

    headers = {"Accept-Language": accept_language} if accept_language else {}
    response = client.delete("/api/v1/tags/999999", headers=headers)

    body = response.json()
    # Der Code ist in allen drei Fällen derselbe — genau das ist der Gewinn:
    # die Assertion ist sprachunabhängig, der Text nur noch Illustration.
    assert body["error_code"] == "tags_not_found"
    assert body["detail"] == erwarteter_text


def test_content_language_header_passt_zur_meldung(envelope_db):
    """Die Middleware setzt ``Content-Language`` aus Accept-Language. Weicht
    sie von der gerenderten Meldung ab, cached ein Proxy die falsche Sprache."""
    inst = _institution(envelope_db)
    user = _user(envelope_db, inst.id, None)
    client = _client(envelope_db, user)

    response = client.delete(
        "/api/v1/tags/999999", headers={"Accept-Language": "fr-CH,fr;q=0.9"}
    )
    assert response.headers["Content-Language"] == "fr"
    assert response.json()["detail"] == "Tag introuvable."


def test_unbekannte_sprache_faellt_auf_deutsch(envelope_db):
    inst = _institution(envelope_db)
    user = _user(envelope_db, inst.id, None)
    client = _client(envelope_db, user)

    response = client.delete(
        "/api/v1/tags/999999", headers={"Accept-Language": "ja-JP,ja;q=0.9"}
    )
    assert response.json()["detail"] == "Tag nicht gefunden."
