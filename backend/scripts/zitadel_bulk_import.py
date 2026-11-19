"""Bulk-Import der Bestandsbenutzer nach tessera/Zitadel (EXAMCRAFT-130).

ADR 0008: Beim Cutover werden alle Bestandsbenutzer mit ihrem bcrypt-Hash in
die Zitadel-Org ``examcraft`` importiert (Admin-API ``ImportData``), danach
wird die Zitadel-``sub`` in ``users.zitadel_sub`` eingetragen.

Drei Schritte, jeder einzeln aufrufbar:

  export    DB lesen, ImportData-JSON schreiben (Datei 0600, enthält Hashes).
  import    Die Datei an ``POST /admin/v1/import`` senden.
  link      ``sub`` aus Zitadel lesen, per E-Mail zuordnen, in
            ``users.zitadel_sub`` schreiben, deaktivierte Benutzer in Zitadel
            deaktivieren. Ohne ``--apply`` nur Trockenlauf (Rollback).

Datenschutz: Hashes und E-Mail-Adressen erscheinen nie in Log oder Ausgabe,
nur Zähler und ``users.id``. Die Export-Datei gehört ausserhalb des
Repositories abgelegt und nach dem Cutover vernichtet (Runbook).

Konfiguration (Umgebung, nie in Dateien):
  ZITADEL_ISSUER           Basis-URL der Instanz
  ZITADEL_ORG_ID           ID der Org ``examcraft``
  ZITADEL_IMPORT_TOKEN     kurzlebiges Token eines Admins (``import``: IAM-Admin,
                           ``link``: Org-User-Manager genügt)

Aufruf (aus ``core/backend``)::

    python -m scripts.zitadel_bulk_import export --out /pfad/import.json
    python -m scripts.zitadel_bulk_import import --file /pfad/import.json
    python -m scripts.zitadel_bulk_import link            # Trockenlauf
    python -m scripts.zitadel_bulk_import link --apply
"""

import argparse
import contextlib
import json
import logging
import os
import stat
import sys
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import quote

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from models.auth import OAuthAccount, User, UserStatus  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "de"
_TIMEOUT_SECONDS = 60.0
# ImportData überträgt alle Benutzer samt bcrypt-Hashes in einem Request.
_IMPORT_TIMEOUT_SECONDS = 600.0
_UNKNOWN_STATE_HINT = "Stand unbekannt, Org prüfen, nicht blind wiederholen"
_PAGE_SIZE = 100
_MAX_PAGES = 1000

# Zitadel-Struktur der IdP-Verknüpfung im Import. Spec/ADR nennen sie
# ``idpLinks``; ``ImportHumanUserRequest`` kennt ``idps`` mit ``configId``,
# ``externalUserId`` und ``displayName``. Unbekannte JSON-Felder verwirft Zitadel
# womöglich still, deshalb im Trockenlauf die Links eines importierten Benutzers
# prüfen (``GET /v2/users/{id}/links``), nicht nur den Login.
IDP_LINKS_FIELD = "idps"
IDP_ID_KEY = "configId"
IDP_EXTERNAL_ID_KEY = "externalUserId"

# ExamCraft-Provider -> Zitadel-IdP-ID kommt per ``--idp``/Umgebung, nicht aus dem Code.


@dataclass
class ExportReport:
    """Zähler und IDs ohne personenbezogene Daten."""

    exported: int = 0
    skipped_pending: list[int] = field(default_factory=list)
    to_deactivate: list[int] = field(default_factory=list)
    without_credentials: list[int] = field(default_factory=list)
    unsupported_hash: list[int] = field(default_factory=list)
    unmapped_providers: dict[str, int] = field(default_factory=dict)
    # users.id mit OAuth-Konten, von denen keines einem IdP zugeordnet werden konnte
    lost_oauth_links: list[int] = field(default_factory=list)
    # users.id, deren normalisierte E-Mail (strip, klein) schon vorkommt: Zitadel
    # lehnt den zweiten userName erst im Import ab (Teilimport).
    duplicate_email: list[int] = field(default_factory=list)

    @property
    def blocking(self) -> bool:
        """Benutzer, die sich nach dem Cutover nicht anmelden könnten."""
        return bool(self.unsupported_hash or self.without_credentials)


def _is_bcrypt(value: str) -> bool:
    """Zitadel akzeptiert ``$2a$``/``$2b$``/``$2y$`` mit Cost 10-16 (EXAMCRAFT-92)."""
    if len(value) != 60 or not value.startswith(("$2a$", "$2b$", "$2y$")):
        return False
    try:
        cost = int(value[4:6])
    except ValueError:
        return False
    return 10 <= cost <= 16


def build_import_data(
    db: Session, org_id: str, idp_ids: Optional[dict[str, str]] = None
) -> tuple[dict[str, Any], ExportReport]:
    """Baut das ``ImportData``-Dokument aus der Benutzertabelle.

    ``status = pending`` wird nicht importiert, deaktivierte Benutzer werden
    importiert und im ``link``-Schritt deaktiviert, unbestätigte E-Mails
    bleiben unbestätigt, ``preferred_language`` NULL wird ``de``.
    """
    idp_ids = idp_ids or {}
    report = ExportReport()
    human_users: list[dict[str, Any]] = []
    seen_emails: set[str] = set()

    links_by_user: dict[int, list[OAuthAccount]] = {}
    for account in db.query(OAuthAccount).order_by(OAuthAccount.id):
        links_by_user.setdefault(account.user_id, []).append(account)

    for user in db.query(User).order_by(User.id):
        if user.status == UserStatus.PENDING.value:
            report.skipped_pending.append(user.id)
            continue

        email_key = user.email.strip().lower()
        if email_key in seen_emails:
            report.duplicate_email.append(user.id)
            continue
        seen_emails.add(email_key)

        entry: dict[str, Any] = {
            "userId": f"examcraft-{user.id}",
            "user": {
                "userName": user.email,
                "profile": {
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "displayName": user.display_name
                    or f"{user.first_name} {user.last_name}".strip(),
                    "preferredLanguage": user.preferred_language or DEFAULT_LANGUAGE,
                },
                "email": {
                    "email": user.email,
                    "isEmailVerified": bool(user.is_email_verified),
                },
                "passwordChangeRequired": False,
            },
        }

        has_password = False
        if user.password_hash:
            if _is_bcrypt(user.password_hash):
                entry["user"]["hashedPassword"] = {
                    "value": user.password_hash,
                    "algorithm": "bcrypt",
                }
                has_password = True
            else:
                report.unsupported_hash.append(user.id)

        links: list[dict[str, str]] = []
        for account in links_by_user.get(user.id, []):
            idp_id = idp_ids.get(account.provider)
            if idp_id is None:
                report.unmapped_providers[account.provider] = (
                    report.unmapped_providers.get(account.provider, 0) + 1
                )
                continue
            links.append(
                {
                    IDP_ID_KEY: idp_id,
                    IDP_EXTERNAL_ID_KEY: account.provider_user_id,
                    "displayName": user.email,
                }
            )
        if links:
            entry["user"][IDP_LINKS_FIELD] = links

        if not has_password and not links:
            if links_by_user.get(user.id):
                report.lost_oauth_links.append(user.id)
            report.without_credentials.append(user.id)
        if user.status != UserStatus.ACTIVE.value:
            report.to_deactivate.append(user.id)

        human_users.append(entry)
        report.exported += 1

    document = {"dataOrgs": {"orgs": [{"orgId": org_id, "humanUsers": human_users}]}}
    return document, report


def write_private_file(path: str, content: dict[str, Any]) -> None:
    """Schreibt die Datei mit 0600 und weigert sich, eine vorhandene zu überschreiben."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(content, handle, ensure_ascii=False)
    except BaseException:
        # Keine halbe Datei mit Hashes zurücklassen. Ein Fehler beim Löschen
        # darf die Ursache nicht überdecken.
        with contextlib.suppress(OSError):
            os.unlink(path)
        raise


# --------------------------------------------------------------------------- #
# Zitadel-Zugriff
# --------------------------------------------------------------------------- #


class ImportError_(Exception):
    """Fehler beim Zitadel-Aufruf. Enthält nie Antwort-Bodies (können PII tragen)."""


def _settings() -> tuple[str, str, str]:
    issuer = os.getenv("ZITADEL_ISSUER", "").strip().rstrip("/")
    org_id = os.getenv("ZITADEL_ORG_ID", "").strip()
    token = os.getenv("ZITADEL_IMPORT_TOKEN", "").strip()
    if not (issuer and org_id and token):
        raise ImportError_(
            "ZITADEL_ISSUER, ZITADEL_ORG_ID und ZITADEL_IMPORT_TOKEN müssen gesetzt sein"
        )
    return issuer, org_id, token


def post_import(path: str, client: Optional[httpx.Client] = None) -> None:
    issuer, _org_id, token = _settings()
    try:
        with open(path, encoding="utf-8") as handle:
            body = json.load(handle)
    except (OSError, ValueError) as exc:
        # Nie den Inhalt (Hashes) ausgeben, nur die Fehlerklasse.
        raise ImportError_(f"Import-Datei nicht lesbar: {type(exc).__name__}") from exc
    owns_client = client is None
    client = client or httpx.Client(timeout=_IMPORT_TIMEOUT_SECONDS)
    try:
        response = client.post(
            f"{issuer}/admin/v1/import",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
    except httpx.TimeoutException as exc:
        # Der Server kann die Daten schon (teilweise) verarbeitet haben.
        raise ImportError_(
            f"ImportData: Zeitüberschreitung ({type(exc).__name__}). {_UNKNOWN_STATE_HINT}"
        ) from exc
    except httpx.HTTPError as exc:
        raise ImportError_(f"Zitadel nicht erreichbar: {type(exc).__name__}") from exc
    finally:
        if owns_client:
            client.close()
    if response.status_code >= 500:
        raise ImportError_(
            f"ImportData: HTTP {response.status_code}. {_UNKNOWN_STATE_HINT}"
        )
    if response.status_code >= 400:
        raise ImportError_(f"ImportData: HTTP {response.status_code}")
    # ImportData meldet Teilfehler im Body (``errors``). Ein nicht lesbarer Body
    # gilt als Fehler: Erfolg ist hier nicht belegt.
    try:
        payload = response.json()
    except ValueError as exc:
        raise ImportError_("ImportData: Antwort nicht lesbar, Stand prüfen") from exc
    if not isinstance(payload, dict):
        raise ImportError_("ImportData: unerwartetes Antwortformat, Stand prüfen")
    errors = payload.get("errors")
    if errors:
        affected = sorted(
            {
                str(e.get("userId") or e.get("id"))
                for e in errors
                if isinstance(e, dict) and (e.get("userId") or e.get("id"))
            }
        )
        raise ImportError_(
            f"ImportData meldete {len(errors)} Fehler (Teilimport möglich, Org prüfen, "
            f"nicht blind wiederholen). Betroffene IDs: {affected or 'unbekannt'}"
        )


def fetch_subs(client: Optional[httpx.Client] = None) -> dict[str, str]:
    """Liest ``{E-Mail (klein): sub}`` aller Human-User der Org ``examcraft``."""
    issuer, org_id, token = _settings()
    owns_client = client is None
    client = client or httpx.Client(timeout=_TIMEOUT_SECONDS)
    headers = {"Authorization": f"Bearer {token}"}
    result: dict[str, str] = {}
    try:
        for page in range(_MAX_PAGES):
            response = client.post(
                f"{issuer}/v2/users",
                headers=headers,
                json={
                    "query": {"offset": page * _PAGE_SIZE, "limit": _PAGE_SIZE},
                    "queries": [
                        {"organizationIdQuery": {"organizationId": org_id}},
                        {"typeQuery": {"type": "TYPE_HUMAN"}},
                    ],
                },
            )
            if response.status_code >= 400:
                raise ImportError_(f"User-Suche: HTTP {response.status_code}")
            try:
                payload = response.json()
            except ValueError as exc:
                raise ImportError_("User-Suche: Antwort nicht lesbar") from exc
            if not isinstance(payload, dict) or "result" not in payload:
                raise ImportError_("User-Suche: unerwartetes Antwortformat")
            users = payload["result"] or []
            for item in users:
                if not isinstance(item, dict):
                    raise ImportError_("User-Suche: unerwartetes Antwortformat")
                email = ((item.get("human") or {}).get("email") or {}).get("email")
                if email and item.get("userId"):
                    key = email.strip().lower()
                    if key in result and result[key] != item["userId"]:
                        # Zwei Zitadel-User mit derselben Adresse: Zuordnung
                        # wäre geraten (Gefahr einer Konto-Übernahme).
                        raise ImportError_(
                            "User-Suche: doppelte E-Mail in der Org, bitte bereinigen"
                        )
                    result[key] = item["userId"]
            if len(users) < _PAGE_SIZE:
                return result
        raise ImportError_("User-Suche: zu viele Seiten")
    except httpx.HTTPError as exc:
        raise ImportError_(f"Zitadel nicht erreichbar: {type(exc).__name__}") from exc
    finally:
        if owns_client:
            client.close()


def deactivate_in_zitadel(sub: str, client: Optional[httpx.Client] = None) -> None:
    issuer, _org_id, token = _settings()
    owns_client = client is None
    client = client or httpx.Client(timeout=_TIMEOUT_SECONDS)
    headers = {"Authorization": f"Bearer {token}"}
    path_sub = quote(sub, safe="")
    try:
        response = client.post(
            f"{issuer}/v2/users/{path_sub}/deactivate", headers=headers, json={}
        )
        if response.status_code < 400:
            return
        # Idempotenz nur, wenn der Benutzer belegt inaktiv ist. Der Fehlertext von
        # Zitadel ist übersetzt und versionsabhängig («User already inactive»), also
        # den Zustand lesen statt den Wortlaut zu raten.
        if response.status_code in (400, 412):
            state = client.get(f"{issuer}/v2/users/{path_sub}", headers=headers)
            if state.status_code < 400 and _user_state(state) == "USER_STATE_INACTIVE":
                return
    except httpx.HTTPError as exc:
        raise ImportError_(f"Zitadel nicht erreichbar: {type(exc).__name__}") from exc
    finally:
        if owns_client:
            client.close()
    raise ImportError_(f"Deaktivieren: HTTP {response.status_code}")


def _user_state(response: httpx.Response) -> Optional[str]:
    try:
        payload = response.json()
    except ValueError:
        return None
    user = payload.get("user") if isinstance(payload, dict) else None
    return user.get("state") if isinstance(user, dict) else None


# --------------------------------------------------------------------------- #
# sub eintragen
# --------------------------------------------------------------------------- #


@dataclass
class LinkReport:
    linked: list[int] = field(default_factory=list)
    already_linked: list[int] = field(default_factory=list)
    conflicts: list[int] = field(default_factory=list)
    unmatched: list[int] = field(default_factory=list)
    to_deactivate: list[tuple[int, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.conflicts and not self.unmatched


def link_subs(db: Session, subs_by_email: dict[str, str]) -> LinkReport:
    """Trägt ``sub`` per E-Mail-Match ein (einmalig, ADR 0008).

    Schreibt in die Session, committet aber nicht: Der Aufrufer entscheidet
    zwischen Trockenlauf (Rollback) und ``--apply`` (Commit). Ein vorhandenes,
    abweichendes ``sub`` wird nie überschrieben.
    """
    report = LinkReport()
    seen: dict[str, int] = {}
    for user in db.query(User).order_by(User.id):
        if user.status == UserStatus.PENDING.value:
            continue
        key = user.email.strip().lower()
        if key in seen:
            # Zwei lokale Benutzer mit derselben normalisierten Adresse würden
            # dieselbe sub erhalten (Unique-Index, falsche Zuordnung).
            report.conflicts.append(user.id)
            continue
        seen[key] = user.id
        sub = subs_by_email.get(key)
        if sub is None:
            report.unmatched.append(user.id)
            continue
        if user.zitadel_sub == sub:
            report.already_linked.append(user.id)
        elif user.zitadel_sub:
            report.conflicts.append(user.id)
            continue
        else:
            user.zitadel_sub = sub
            report.linked.append(user.id)
        if user.status != UserStatus.ACTIVE.value:
            report.to_deactivate.append((user.id, sub))
    db.flush()
    return report


def _parse_idps(values: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for value in values:
        provider, sep, idp_id = value.partition("=")
        if not sep or not provider or not idp_id:
            raise ImportError_("--idp erwartet provider=idpId (z. B. google=123)")
        mapping[provider] = idp_id
    return mapping


def _run_export(db: Session, args: argparse.Namespace) -> int:
    org_id = os.getenv("ZITADEL_ORG_ID", "").strip()
    if not org_id:
        raise ImportError_("ZITADEL_ORG_ID muss gesetzt sein")
    document, report = build_import_data(db, org_id, _parse_idps(args.idp))
    print(
        f"exportiert={report.exported} pending_uebersprungen={report.skipped_pending} "
        f"zu_deaktivieren={report.to_deactivate} "
        f"ohne_anmeldeweg={report.without_credentials} "
        f"davon_oauth_ohne_mapping={report.lost_oauth_links} "
        f"hash_nicht_importierbar={report.unsupported_hash} "
        f"doppelte_email={report.duplicate_email} "
        f"idp_ohne_mapping={report.unmapped_providers}"
    )
    if report.unsupported_hash or report.duplicate_email:
        print(
            "Abbruch: nicht importierbare Hashes oder doppelte E-Mail-Adressen "
            "(vorher in der DB bereinigen), keine Datei geschrieben.",
            file=sys.stderr,
        )
        return 1
    if report.without_credentials and not args.allow_without_credentials:
        print(
            "Abbruch: Benutzer ohne gültigen Anmeldeweg, keine Datei geschrieben "
            "(ohne_anmeldeweg bewusst mit --allow-without-credentials freigeben).",
            file=sys.stderr,
        )
        return 1
    if report.unmapped_providers and not args.allow_unmapped_idps:
        print(
            "Abbruch: OAuth-Provider ohne --idp-Zuordnung, ihre Links gingen verloren "
            "(Tippfehler prüfen, bewusst mit --allow-unmapped-idps freigeben).",
            file=sys.stderr,
        )
        return 1
    write_private_file(args.out, document)
    print("Datei geschrieben (0600).")
    return 0


def _run_link(db: Session, apply: bool) -> int:
    try:
        report = link_subs(db, fetch_subs())
    except SQLAlchemyError as exc:
        # z. B. Unique-Verletzung auf zitadel_sub: nichts ist geschrieben.
        db.rollback()
        raise ImportError_(
            f"sub eintragen fehlgeschlagen ({type(exc).__name__}), nichts geschrieben"
        ) from exc
    print(
        f"verknuepft={report.linked} bereits={report.already_linked} "
        f"konflikt={report.conflicts} ohne_treffer={report.unmatched} "
        f"zu_deaktivieren={[uid for uid, _ in report.to_deactivate]}"
    )
    if not apply:
        db.rollback()
        print("Trockenlauf: nichts geschrieben (--apply zum Schreiben).")
        return 0 if report.ok else 1
    if not report.ok:
        db.rollback()
        print("Abbruch: Konflikte oder Benutzer ohne Treffer, nichts geschrieben.")
        return 1
    # Zuerst deaktivieren, dann committen: Ein Fehler hinterlässt höchstens
    # deaktivierte Zitadel-User ohne eingetragene sub, ein Wiederholungslauf ist
    # idempotent. Umgekehrt blieben Gesperrte angemeldet.
    failed: list[int] = []
    for user_id, zitadel_sub in report.to_deactivate:
        try:
            deactivate_in_zitadel(zitadel_sub)
        except ImportError_ as exc:
            failed.append(user_id)
            logger.error("Deaktivieren fehlgeschlagen (users.id=%s): %s", user_id, exc)
    if failed:
        db.rollback()
        print(
            f"Abbruch: Deaktivierung fehlgeschlagen für users.id={failed}, "
            "nichts committed. `link --apply` erneut ausführen (idempotent).",
            file=sys.stderr,
        )
        return 2
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        done = [uid for uid, _ in report.to_deactivate]
        raise ImportError_(
            f"Commit fehlgeschlagen ({type(exc).__name__}). Teilzustand: in Zitadel "
            f"deaktiviert für users.id={done}, DB ohne sub. `link --apply` erneut "
            "ausführen (idempotent)."
        ) from exc
    print(
        f"sub eingetragen ({len(report.linked)}), "
        f"deaktiviert ({len(report.to_deactivate)})."
    )
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser("export", help="ImportData-JSON schreiben")
    p_export.add_argument("--out", required=True)
    p_export.add_argument(
        "--allow-without-credentials",
        action="store_true",
        help="Benutzer ohne Passwort und ohne IdP-Link trotzdem exportieren",
    )
    p_export.add_argument(
        "--allow-unmapped-idps",
        action="store_true",
        help="OAuth-Konten ohne --idp-Zuordnung bewusst ohne Link exportieren",
    )
    p_export.add_argument(
        "--idp",
        action="append",
        default=[],
        help="provider=zitadelIdpId (google, microsoft, github), mehrfach",
    )

    p_import = sub.add_parser("import", help="Datei an Zitadel senden")
    p_import.add_argument("--file", required=True)

    p_link = sub.add_parser("link", help="sub eintragen, Deaktivierte deaktivieren")
    p_link.add_argument("--apply", action="store_true")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        if args.command == "import":
            post_import(args.file)
            print("ImportData erfolgreich gesendet.")
            return 0

        from database import SessionLocal

        db = SessionLocal()
        try:
            if args.command == "export":
                return _run_export(db, args)
            return _run_link(db, args.apply)
        finally:
            db.close()
    except (ImportError_, OSError, SQLAlchemyError, httpx.InvalidURL) as exc:
        # Fremde Fehler: nur den Typ nennen, nie den Text (kann Pfade, DB-Host,
        # SQL-Parameter oder Inhalte enthalten).
        msg = str(exc) if isinstance(exc, ImportError_) else type(exc).__name__
        print(f"Fehler: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
