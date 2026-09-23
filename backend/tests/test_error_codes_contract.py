"""Contract-Test für die Fehlercodes (TF-773 Teil E).

Die Aussage des ADR (docs/adr/0005) ist: **der Code IST der Locale-Schlüssel**.
Diese Datei ist die Stelle, an der diese Aussage gehalten wird — sonst ist sie
Prosa. Genau dafür wurde in Teil A die Punktnotation verworfen: die Prüfung
darf ein exakter Mengenvergleich sein und keine Abbildungsregel, die selbst
gepflegt werden muss.

Der Scan läuft über den AST aller drei Tiers, nicht über Regex — ein
mehrzeiliger Aufruf oder ein Kommentar mit ``api_error(`` darin würde eine
Textsuche sonst in beide Richtungen täuschen.

Zwei Aufrufformen, zwei Regeln:

* ``api_error(status, "key", locale)`` — die Meldung kommt aus den Locales,
  also **muss** der Schlüssel existieren.
* ``AppHTTPException(status, <text>, error_code="key")`` — die Meldung ist
  bewusst eine andere (durchgereichter ``str(exc)`` einer Service-Exception,
  konkreter als jeder generische Satz), also darf hier **kein** Locale-Schlüssel
  verlangt werden. Diese Codes sind trotzdem Teil des Vertrags nach aussen und
  werden unten auf Namenskonvention und Eindeutigkeit geprüft.

Abgrenzung: geprüft wird nur gegen ``de``. Dass en/fr/it dieselben Schlüssel
tragen, ist die Zuständigkeit von ``test_locale_parity.py`` — die einzige
Stelle, an der die Sprachparität der Backend-Locales hängt. Beides hier zu
prüfen wäre dieselbe Aussage in zwei Gates.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
LOCALES_DIR = pathlib.Path(__file__).resolve().parents[1] / "locales"
TIERS = ("core", "premium", "enterprise")

# Von den Framework-Handlern in main.py erzeugt, nie aus Endpunkt-Code
# geworfen — der Scan sieht sie deshalb nicht, der Vertrag umfasst sie aber.
from errors import RESERVED_ERROR_CODES  # noqa: E402


# Die Fabrik selbst: dort steht ``AppHTTPException(..., error_code=code)`` mit
# einer Variablen — das ist die Implementierung von api_error, keine
# Aufrufstelle, und würde den Scan in beiden Richtungen verfälschen.
FACTORY_MODULE = "core/backend/errors.py"


def _iter_source_files():
    for tier in TIERS:
        root = REPO_ROOT / tier
        if not root.is_dir():
            # core/-Mirror: premium/ und enterprise/ fehlen dort komplett.
            # Kein Grund, den Test rot zu färben — er prüft dann eben nur core.
            continue
        for path in sorted(root.rglob("*.py")):
            s = str(path)
            if "/tests/" in s or "/.venv" in s or "/node_modules/" in s:
                continue
            if str(path.relative_to(REPO_ROOT)) == FACTORY_MODULE:
                continue
            yield path


def _collect_codes():
    """(api_error-Codes, AppHTTPException-Codes, dynamische Stellen)."""
    translated: dict[str, list[str]] = {}
    passthrough: dict[str, list[str]] = {}
    dynamic: list[str] = []

    for path in _iter_source_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - defekte Datei bricht anderswo
            continue
        rel = str(path.relative_to(REPO_ROOT))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")

            if name == "api_error":
                arg = node.args[1] if len(node.args) >= 2 else None
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    translated.setdefault(arg.value, []).append(f"{rel}:{node.lineno}")
                else:
                    dynamic.append(f"{rel}:{node.lineno}")

            elif name == "AppHTTPException":
                kw = next((k for k in node.keywords if k.arg == "error_code"), None)
                if kw is None:
                    dynamic.append(f"{rel}:{node.lineno} (ohne error_code)")
                elif isinstance(kw.value, ast.Constant) and isinstance(
                    kw.value.value, str
                ):
                    passthrough.setdefault(kw.value.value, []).append(
                        f"{rel}:{node.lineno}"
                    )
                else:
                    dynamic.append(f"{rel}:{node.lineno}")

    return translated, passthrough, dynamic


TRANSLATED, PASSTHROUGH, DYNAMIC = _collect_codes()


def _locale_dirs() -> list[pathlib.Path]:
    """Core plus every tier that ships its own ``backend/locales`` (ADR 0006).

    A premium endpoint's ``api_error`` code lives in ``premium/backend/
    locales``, not in core's — the union is what ``translation_service.t()``
    resolves against at runtime once the tier is registered. Missing tier
    directories are skipped for the same reason as in ``_iter_source_files``:
    the core mirror has neither the code nor the locales.
    """
    dirs = [LOCALES_DIR]
    for tier in TIERS:
        candidate = REPO_ROOT / tier / "backend" / "locales"
        if tier != "core" and candidate.is_dir():
            dirs.append(candidate)
    return dirs


def _locale_keys(lang: str) -> set[str]:
    keys: set[str] = set()
    for locale_dir in _locale_dirs():
        doc = json.loads((locale_dir / f"t.{lang}.json").read_text(encoding="utf-8"))
        keys |= set(doc[lang])
    return keys


def test_es_gibt_ueberhaupt_codes():
    """Sanity-Check gegen einen kaputten Scan.

    Ohne ihn wäre ein Scan, der versehentlich null Dateien liest, in jedem
    anderen Test dieser Datei grün — der teuerste Fehlermodus eines Wächters.
    """
    assert len(TRANSLATED) > 100, (
        f"Nur {len(TRANSLATED)} api_error-Codes gefunden — der AST-Scan greift "
        f"vermutlich nicht mehr (Aufrufname geändert? Verzeichnis verschoben?)."
    )


# Absichtlich nur gegen ``de`` und nicht über alle vier Sprachen parametrisiert:
# die Sprachparität ist die Zuständigkeit von test_locale_parity.py, und ein in
# de vorhandener Schlüssel liegt damit auch in en/fr/it. Vierfach zu prüfen
# hiesse, dieselbe Aussage in zwei Gates zu halten — und ein einzelner fehlender
# Schlüssel würde vier fast gleiche Fehlermeldungen erzeugen, von denen keine
# sagt, wo das Problem wirklich sitzt.
_REFERENCE_LANG = "de"


def test_jeder_api_error_code_hat_einen_schluessel():
    keys = _locale_keys(_REFERENCE_LANG)
    missing = {
        code: sites for code, sites in sorted(TRANSLATED.items()) if code not in keys
    }
    assert not missing, (
        f"{len(missing)} api_error-Code(s) ohne Schlüssel in "
        f"t.{_REFERENCE_LANG}.json:\n"
        + "\n".join(f"  {c}  ({', '.join(s[:3])})" for c, s in missing.items())
        + "\nDer Code IST der Locale-Schlüssel (docs/adr/0005) — lege den "
        "Schlüssel in allen vier Sprachen an, statt den Code umzubenennen: "
        "Core-Codes in core/backend/locales, Premium-Codes in "
        "premium/backend/locales (docs/adr/0006). "
        "Ob alle vier gleichziehen, prüft test_locale_parity.py."
    )


def test_reservierte_codes_haben_einen_schluessel():
    keys = _locale_keys(_REFERENCE_LANG)
    missing = [c for c in RESERVED_ERROR_CODES if c not in keys]
    assert not missing, (
        f"Reservierte Codes ohne Schlüssel in t.{_REFERENCE_LANG}.json: "
        f"{missing}. Die Handler in main.py rendern sie, ohne durch api_error "
        f"zu gehen."
    )


def test_keine_dynamischen_codes_ohne_konstante():
    """Ein aus einer Variablen gebauter Code ist für diesen Test unsichtbar.

    Erlaubt sind sie trotzdem — aber nur dort, wo die Variable nachweislich
    einen Locale-Schlüssel hält (``t(e.code, …)`` aus TransferError,
    ``detail_key`` in document_visibility). Neue Stellen müssen hier
    eingetragen werden, damit die Lücke sichtbar bleibt statt zu wachsen.
    """
    ERLAUBT = {
        "core/backend/api/admin.py",  # TransferError.code
        "core/backend/utils/document_visibility.py",  # detail_key-Parameter
        "core/backend/api/submissions.py",  # ImportDriverError.code
        "premium/backend/api/v1/wizard.py",  # WizardServiceError.code
    }
    unerwartet = [d for d in DYNAMIC if d.rsplit(":", 1)[0] not in ERLAUBT]
    assert not unerwartet, (
        "api_error/AppHTTPException mit nicht-konstantem Code an:\n  "
        + "\n  ".join(unerwartet)
        + "\nDiese Stellen entziehen sich dem Contract-Test. Entweder eine "
        "Konstante verwenden oder hier mit Begründung eintragen."
    )


def test_erlaubte_dynamische_quellen_liefern_nur_echte_schluessel():
    """Der Test oben prüft nur, DASS eine Stelle in ``ERLAUBT`` steht — nie,
    WELCHE Werte ihre Variable tatsächlich annehmen kann. "Nachweislich einen
    Locale-Schlüssel hält" war bisher nur eine Behauptung im Docstring; hier
    der tatsächliche Nachweis, für beide heutigen Einträge (TF-773 review).
    """
    keys = _locale_keys(_REFERENCE_LANG)

    # admin.py: TransferError.code — endlich viele Literale, extrahiert aus
    # jedem `TransferError("...", ...)`-Aufruf im Service selbst statt von
    # Hand abgeschrieben, damit ein neuer Code hier automatisch mitläuft.
    transfer_service = (
        REPO_ROOT / "core/backend/services/user_institution_transfer_service.py"
    )
    tree = ast.parse(transfer_service.read_text(encoding="utf-8"))
    transfer_codes = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "TransferError"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }
    assert transfer_codes, (
        "TransferError-Scan hat nichts gefunden — Klasse umbenannt oder verschoben?"
    )
    fehlend_transfer = sorted(c for c in transfer_codes if c not in keys)
    assert not fehlend_transfer, (
        f"TransferError-Code(s) ohne Schlüssel in t.{_REFERENCE_LANG}.json: "
        f"{fehlend_transfer}"
    )

    # document_visibility.py: assert_document_visible_for()'s `detail_key` —
    # geprüft wird der Default UND, dass niemand im Repo ihn überschreibt;
    # würde das doch jemand tun, soll dieser Test rot werden statt den neuen
    # Wert lautlos ungeprüft zu lassen.
    visibility_module = REPO_ROOT / "core/backend/utils/document_visibility.py"
    tree = ast.parse(visibility_module.read_text(encoding="utf-8"))
    default_value = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "assert_document_visible_for"
        ):
            for arg, default in zip(
                reversed(node.args.kwonlyargs), reversed(node.args.kw_defaults)
            ):
                if arg.arg == "detail_key" and isinstance(default, ast.Constant):
                    default_value = default.value
    assert default_value is not None, (
        "assert_document_visible_for()'s detail_key-Default nicht gefunden — "
        "Signatur geändert?"
    )
    assert default_value in keys, (
        f"detail_key-Default {default_value!r} fehlt in t.{_REFERENCE_LANG}.json"
    )

    override_sites = [
        f"{path.relative_to(REPO_ROOT)}:{m.start()}"
        for path in _iter_source_files()
        for m in re.finditer(r"detail_key\s*=", path.read_text(encoding="utf-8"))
        if str(path.relative_to(REPO_ROOT))
        != "core/backend/utils/document_visibility.py"
    ]
    assert not override_sites, (
        "detail_key= wird jetzt irgendwo überschrieben: "
        + ", ".join(override_sites)
        + " — den tatsächlichen Wert hier ergänzen und gegen die "
        "Locale-Datei prüfen, statt dies weiterhin ungeprüft zu lassen."
    )


def test_wizard_service_error_liefert_nur_echte_schluessel():
    """``premium/backend/api/v1/wizard.py`` wirft ``api_error(e.http_status,
    e.code, …)`` — derselbe Fall wie ``TransferError`` oben, nur im
    Premium-Tier (TF-773 PR 2b). Jeder ``WizardServiceError(...)``-Aufruf muss
    einen Literal-Code tragen, sonst wäre der Wert für diesen Test unsichtbar.

    Im ``core/``-Mirror fehlt ``premium/`` — dann gibt es auch keinen Aufrufer.
    """
    service = REPO_ROOT / "premium/backend/services/prompt_wizard_service.py"
    if not service.is_file():
        return

    keys = _locale_keys(_REFERENCE_LANG)
    tree = ast.parse(service.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "WizardServiceError"
    ]
    assert calls, "WizardServiceError-Scan hat nichts gefunden — Klasse umbenannt?"

    nicht_literal = [
        node.lineno
        for node in calls
        if not (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        )
    ]
    assert not nicht_literal, (
        f"WizardServiceError ohne Literal-Code in Zeile(n) {nicht_literal}"
    )

    fehlend = sorted({n.args[0].value for n in calls} - keys)
    assert not fehlend, (
        f"WizardServiceError-Code(s) ohne Schlüssel in t.{_REFERENCE_LANG}.json: "
        f"{fehlend}"
    )


IMPORT_MODULES = (
    "core/backend/services/import_service.py",
    "core/backend/services/import_drivers/base.py",
    "core/backend/services/import_drivers/moodle_json_driver.py",
    "core/backend/services/import_drivers/moodle_api_driver.py",
)


def _import_error_classes(trees: dict[str, ast.Module]) -> set[str]:
    """Every exception class in the import modules that carries a code.

    Derived from the sources rather than listed by hand: a new
    ``class MoodleQuotaError(ImportDriverError)`` inherits the two-argument
    constructor and therefore the contract, and a hand-written list would not
    notice it. Iterated to a fixed point because the classes form a chain
    (``ColumnMappingError`` -> ``ImportDriverError``, ``UnknownDriverError``
    -> ``ImportValidationError`` -> ``ImportDriverError``).
    """
    classes = {"ImportDriverError"}
    while True:
        grown = set(classes)
        for tree in trees.values():
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and any(
                    isinstance(base, ast.Name) and base.id in classes
                    for base in node.bases
                ):
                    grown.add(node.name)
        if grown == classes:
            return classes
        classes = grown


def test_import_fehlercodes_sind_echte_schluessel():
    """``api/submissions.py`` passes ``exc.code`` to ``api_error()``.

    The entry in ``ERLAUBT`` above only records that the site exists. This is
    the proof the docstring there demands: the variable is filled exclusively
    by the import exceptions, whose first constructor argument is a literal
    everywhere, and every one of those literals must resolve in the locales.
    Same shape as the ``TransferError`` proof above, for the same reason —
    a code invented at a throw site would otherwise reach a teacher as the
    raw key.
    """
    keys = _locale_keys(_REFERENCE_LANG)

    trees = {
        rel: ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
        for rel in IMPORT_MODULES
    }
    error_classes = _import_error_classes(trees)
    assert len(error_classes) > 1, (
        "Nur ImportDriverError gefunden — die Subklassen wurden umbenannt "
        "oder verschoben, und der Scan unten prüft dann fast nichts."
    )

    codes: dict[str, list[str]] = {}
    dynamisch: list[str] = []
    for rel, tree in trees.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not (isinstance(node.func, ast.Name) and node.func.id in error_classes):
                continue
            arg = node.args[0] if node.args else None
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                codes.setdefault(arg.value, []).append(f"{rel}:{node.lineno}")
            else:
                dynamisch.append(f"{rel}:{node.lineno}")

    assert not dynamisch, (
        "Import-Exception ohne konstanten Code an:\n  "
        + "\n  ".join(dynamisch)
        + "\nDamit ist der Wert für diesen Test unsichtbar — Konstante "
        "verwenden."
    )
    assert len(codes) >= 10, (
        f"Nur {len(codes)} Import-Codes gefunden. PR 2c hat die Wurfstellen "
        "bewusst auf unterscheidbare Codes aufgeteilt; ein Zusammenfallen auf "
        "wenige Sammelcodes nimmt der Lehrperson genau die Unterscheidung "
        "wieder weg, für die dieser PR gemacht wurde."
    )
    fehlend = {c: sites for c, sites in sorted(codes.items()) if c not in keys}
    assert not fehlend, (
        f"Import-Code(s) ohne Schlüssel in t.{_REFERENCE_LANG}.json:\n"
        + "\n".join(f"  {c}  ({', '.join(s[:3])})" for c, s in fehlend.items())
    )


FRONTEND_CODES_FILE = "core/frontend/src/errors/codes/submissions.ts"


def test_import_codes_sind_im_frontend_registriert():
    """A backend code the frontend does not list is invisible to the user.

    ``errors/codes/*.ts`` is an accept-list: ``selectCode()`` drops an
    ``error_code`` that is not in it and falls back to the caller's generic
    operation sentence. Nothing fails — not the request, not a type, not any
    other test in this file. The user simply reads «Vorschau fehlgeschlagen.»
    where the backend had something specific to say, and the only trace is a
    ``console.warn`` in a browser nobody is watching.

    So the two sides are tied together here, for the import prefix TF-773
    PR 2c owns. Deliberately not for every code in the repo: several backend
    codes are unreachable from any call site and belong in no accept-list
    (``codes/submissions.ts`` documents ``submissions_grade_export_internal_error``
    as one), and deciding that per code is not this test's job.
    """
    trees = {
        rel: ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
        for rel in IMPORT_MODULES
    }
    error_classes = _import_error_classes(trees)
    raised = {
        node.args[0].value
        for tree in trees.values()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in error_classes
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    # The endpoint raises this one itself (broker outage), outside the driver
    # exceptions the scan above sees.
    raised.add("submissions_import_enqueue_failed")

    registered_source = (REPO_ROOT / FRONTEND_CODES_FILE).read_text(encoding="utf-8")
    registered = set(re.findall(r"'(submissions_[a-z0-9_]+)'", registered_source))
    assert len(registered) > 5, (
        f"{FRONTEND_CODES_FILE} scheint leer oder umgebaut — der Scan findet "
        f"nur {len(registered)} Codes."
    )

    # Raised by the service, but a guard in front of it answers first — no
    # endpoint can produce them, so the registry must not list them either
    # (AppError.ts: "a code belongs here only if some endpoint or call site can
    # actually produce it"). Shared with the test that pins the two guards, so
    # the exemption and its proof cannot drift apart.
    from tests.test_submissions_import_error_codes import HTTP_UNERREICHBAR

    unerreichbar = set(HTTP_UNERREICHBAR)
    assert unerreichbar <= raised, (
        f"Ausnahme für Codes, die niemand mehr wirft: {sorted(unerreichbar - raised)}"
    )
    zu_viel = sorted(unerreichbar & registered)
    assert not zu_viel, (
        f"Über HTTP unerreichbare Code(s) in {FRONTEND_CODES_FILE} registriert: "
        f"{zu_viel}. Entweder den Wächter davor entfernen (dann aus "
        "HTTP_UNERREICHBAR nehmen) oder die Registrierung zurücknehmen."
    )

    fehlend = sorted((raised - unerreichbar) - registered)
    assert not fehlend, (
        f"Import-Code(s) nicht in {FRONTEND_CODES_FILE} registriert:\n  "
        + "\n  ".join(fehlend)
        + "\nDas Frontend verwirft sie still und zeigt den Sammelsatz der "
        "Operation. Eintragen und in allen vier core/frontend/src/locales "
        "übersetzen."
    )


def test_passthrough_codes_folgen_der_namenskonvention():
    """``AppHTTPException``-Codes haben keinen Locale-Schlüssel, sind aber
    trotzdem öffentlicher Vertrag — sie müssen wie Locale-Schlüssel aussehen,
    damit ein Client sie nicht von einem Freitext unterscheiden muss."""
    schema = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")
    falsch = sorted(c for c in PASSTHROUGH if not schema.match(c))
    assert not falsch, (
        f"Codes ohne snake_case-Namensraumpräfix: {falsch}. "
        f"Konvention ist <modul>_<sache>, wie bei den Locale-Schlüsseln."
    )


def test_kein_code_ist_gleichzeitig_uebersetzt_und_durchgereicht():
    """Derselbe Code in beiden Formen hiesse: mal kommt die Meldung aus den
    Locales, mal aus einer Exception. Für den Client ist der Code dann keine
    Zusage mehr über den Inhalt."""
    beides = sorted(set(TRANSLATED) & set(PASSTHROUGH))
    assert not beides, (
        f"Code sowohl via api_error als auch via AppHTTPException: {beides}"
    )
