"""Jeder Backend-Locale-Schlüssel wird vom Code auch benutzt (TF-775 Teil B).

``test_locale_parity.py`` prüft, dass die vier Sprachen dieselben Schlüssel
haben — nicht, ob irgendein Code sie noch braucht. So hatten sich in
``core/backend/locales/`` 22 Schlüssel angesammelt, die keine ``.py``-Datei mehr
warf (u. a. ``auth_session_expired``, ``server_error``, drei ``billing_*``).
Sie wurden in TF-775 Teil B gelöscht; dieser Test verhindert, dass sich
dieselbe Klasse wieder aufbaut.

Methode wie im Frontend-Gate (``core/frontend/scripts/check-i18n-keys.ts``,
Teil C): Ein Schlüssel gilt als benutzt, wenn er irgendwo im Produktionscode
seines Tiers als String-Literal steht — ``api_error(…, "key", …)``,
``t("key")``, ``code = "key"`` in einer Exception-Klasse. Ob das Literal
tatsächlich bei ``t()`` ankommt, prüft der Test nicht; er irrt also nur in
Richtung «benutzt», nie so, dass ein gebrauchter Schlüssel gelöscht wird.
Tests zählen nicht: ein Schlüssel, den nur ein Test erwähnt, ist tot.

Schlüssel, die der Code zur Laufzeit zusammensetzt (``t(f"export_type_{…}")``),
stehen in ``DYNAMISCHE_PRAEFIXE``. Jeder Eintrag muss im Code noch vorkommen.
Neue Aufrufstellen der Form ``t(f"…{…}")`` / ``api_error(…, f"…{…}")`` erkennt
der Test selbst und verlangt einen Eintrag. Einen Schlüssel, der über eine
Variable (``key = f"x_{y}"; t(key)``), eine Verkettung oder einen qualifizierten
Aufruf (``service.t(f"…")``) zusammengesetzt wird, sieht er nicht — er meldet
die betroffenen Schlüssel dann als unbenutzt. Die Antwort darauf ist, den
Aufruf auf die erkannte Form umzubauen, nicht, die Schlüssel zu löschen.

Core-Schlüssel gelten als benutzt, wenn irgendein vorhandenes Tier sie nennt:
Premium wirft Core-Codes (``documents_not_found`` in
``premium/backend/api/v1/vector_search.py``), und die Übersetzung kommt aus den
Core-Locales. Premium- und Enterprise-Schlüssel zählen nur gegen den eigenen
Code — Core darf die anderen Tiers nicht referenzieren. Die Präfixliste gilt
tier-übergreifend. Im ``core/``-Mirror fehlen Premium und Enterprise; dort
zählt nur der Core-Code, was reicht, solange Core jeden eigenen Schlüssel auch
selbst benutzt. Ein Tier, das fehlt, obwohl sein Verzeichnis da ist, schlägt
fehl statt still wegzufallen — ebenso jedes fehlende Tier, wenn
``I18N_REQUIRE_ALL_TIERS`` gesetzt ist (private CI, wie beim Frontend-Gate).
"""

from __future__ import annotations

import json
import os
import pathlib
import re

import pytest

CORE_BACKEND = pathlib.Path(__file__).resolve().parents[1]
#: Im privaten Repo liegt das Backend unter ``core/backend``; im ``core/``-Mirror
#: direkt unter ``backend/``. ``parents[3]`` zeigte dort über den Checkout hinaus.
REPO_ROOT = (
    CORE_BACKEND.parents[1]
    if CORE_BACKEND.parent.name == "core"
    else CORE_BACKEND.parent
)

#: Präfix → Fundstelle. Der Präfix deckt alle Schlüssel ab, die mit ihm beginnen.
DYNAMISCHE_PRAEFIXE: dict[str, str] = {
    "export_type_": "services/exam_export_service.py::_type_label, "
    "t(f'export_type_{question_type}') für die Fragetypen im Export",
}

_SKIP_DIRS = {"tests", "locales", "__pycache__", ".venv", "node_modules"}

#: ``t(f"prefix_{…}")`` oder ``api_error(…, f"prefix_{…}")`` — ein Schlüssel,
#: den ein Literal-Scan nicht sieht. Nur der statische Kopf wird erfasst.
_DYNAMISCHER_AUFRUF = re.compile(
    r"""(?<![\w.])(?:t|api_error)\([^()]*?\bf(["'])([a-z0-9_]*)\{"""
)


#: Tiers ausserhalb von Core, die eigene Locales haben (müssen).
_TIERS_MIT_LOCALES = ("premium",)
_ANDERE_TIERS = ("premium", "enterprise")


def _tier_layout() -> tuple[
    dict[str, pathlib.Path], dict[str, pathlib.Path], list[str]
]:
    """Code-Verzeichnisse je Tier, Tiers mit Locales, und Layout-Fehler."""
    code = {"core": CORE_BACKEND}
    locales = {"core": CORE_BACKEND}
    fehler = []
    require_all = bool(os.environ.get("I18N_REQUIRE_ALL_TIERS"))
    for tier in _ANDERE_TIERS:
        backend = REPO_ROOT / tier / "backend"
        if not backend.is_dir():
            if (REPO_ROOT / tier).is_dir() or require_all:
                fehler.append(f"{tier}/backend fehlt")
            continue
        code[tier] = backend
        if (backend / "locales").is_dir():
            locales[tier] = backend
        elif tier in _TIERS_MIT_LOCALES:
            fehler.append(f"{tier}/backend/locales fehlt")
    return code, locales, fehler


CODE_DIRS, TIER_DIRS, LAYOUT_FEHLER = _tier_layout()


def _produktionsquellen(backend: pathlib.Path) -> dict[pathlib.Path, str]:
    quellen = {}
    for path in backend.rglob("*.py"):
        rel = path.relative_to(backend)
        if _SKIP_DIRS.intersection(rel.parts[:-1]) or path.name.startswith("test_"):
            continue
        quellen[path] = path.read_text(encoding="utf-8")
    return quellen


def _schluessel(backend: pathlib.Path) -> list[str]:
    doc = json.loads((backend / "locales" / "t.de.json").read_text(encoding="utf-8"))
    return list(doc["de"])


def _literale(quellen: dict[pathlib.Path, str]) -> set[str]:
    literal = re.compile(r"""(["'])([a-z][a-z0-9_]*)\1""")
    return {m.group(2) for text in quellen.values() for m in literal.finditer(text)}


def unbenutzte_schluessel(
    schluessel: list[str], literale: set[str], praefixe: list[str]
) -> list[str]:
    return sorted(
        key
        for key in schluessel
        if key not in literale and not any(key.startswith(p) for p in praefixe)
    )


def literale_fuer(tier: str, literale_je_tier: dict[str, set[str]]) -> set[str]:
    """Core-Schlüssel darf jedes Tier benutzen, die anderen nur ihr eigenes."""
    if tier == "core":
        return set().union(*literale_je_tier.values())
    return literale_je_tier[tier]


def test_core_quellen_werden_gefunden():
    """Sanity-Check: ein verschobenes Verzeichnis darf den Test nicht dadurch
    grün machen, dass er gar nichts mehr liest."""
    quellen = _produktionsquellen(CORE_BACKEND)
    assert len(quellen) > 100
    assert len(_schluessel(CORE_BACKEND)) > 100


def test_tier_layout_ist_vollstaendig():
    """Ein umbenanntes Tier-Verzeichnis darf seine Schlüssel nicht still aus der
    Prüfung nehmen."""
    assert not LAYOUT_FEHLER, (
        f"Backend-Tiers fehlen: {LAYOUT_FEHLER}. Umbenannt oder verschoben? "
        f"Dann _tier_layout() nachziehen."
    )


@pytest.mark.parametrize("tier", list(TIER_DIRS))
def test_jeder_schluessel_wird_benutzt(tier: str):
    literale_je_tier = {
        name: _literale(_produktionsquellen(backend))
        for name, backend in CODE_DIRS.items()
    }
    unbenutzt = unbenutzte_schluessel(
        _schluessel(TIER_DIRS[tier]),
        literale_fuer(tier, literale_je_tier),
        list(DYNAMISCHE_PRAEFIXE),
    )
    assert not unbenutzt, (
        f"{tier}: {len(unbenutzt)} Schlüssel in locales/t.*.json, die kein "
        f"Produktionscode als Literal nennt: {unbenutzt}. Setzt der Code sie "
        f"zusammen (Variable, Verkettung, service.t(f'…')), den Aufruf auf "
        f"t(f'präfix_{{…}}') umbauen und den Präfix in DYNAMISCHE_PRAEFIXE "
        f"eintragen. Sonst in allen vier Sprachen löschen."
    )


def test_dynamische_praefixe_sind_vollstaendig_und_aktuell():
    gefunden: dict[str, set[str]] = {}
    for backend in CODE_DIRS.values():
        for path, text in _produktionsquellen(backend).items():
            for m in _DYNAMISCHER_AUFRUF.finditer(text):
                gefunden.setdefault(m.group(2), set()).add(
                    str(path.relative_to(REPO_ROOT))
                )

    neu = {p: sorted(f) for p, f in gefunden.items() if p not in DYNAMISCHE_PRAEFIXE}
    veraltet = sorted(p for p in DYNAMISCHE_PRAEFIXE if p not in gefunden)
    assert not neu, (
        f"Zusammengesetzte Schlüssel ohne Eintrag in DYNAMISCHE_PRAEFIXE: {neu}"
    )
    assert not veraltet, (
        f"DYNAMISCHE_PRAEFIXE nennt Präfixe, die kein Code mehr zusammensetzt: "
        f"{veraltet}. Eintrag entfernen."
    )


def test_erkennung_an_fixture():
    """Die reine Logik, damit ein kaputter Filter nicht still alles durchlässt."""
    schluessel = ["a_used", "b_dead", "export_type_x", "c_dead"]
    assert unbenutzte_schluessel(schluessel, {"a_used"}, ["export_type_"]) == [
        "b_dead",
        "c_dead",
    ]
    assert _DYNAMISCHER_AUFRUF.search('return t(f"export_type_{q}", locale=x)')
    assert _DYNAMISCHER_AUFRUF.search("api_error(400, f'foo_{x}', locale)")
    assert not _DYNAMISCHER_AUFRUF.search('print(f"export_type_{q}")')

    # Ein Core-Schlüssel, den nur Premium wirft, ist für Core benutzt — ein
    # Premium-Schlüssel, den nur Core nennt, für Premium nicht.
    literale_je_tier = {"core": {"core_own"}, "premium": {"core_via_premium", "p_own"}}
    assert (
        unbenutzte_schluessel(
            ["core_own", "core_via_premium"],
            literale_fuer("core", literale_je_tier),
            [],
        )
        == []
    )
    literale_je_tier["core"].add("p_only_core")
    assert unbenutzte_schluessel(
        ["p_own", "p_only_core"], literale_fuer("premium", literale_je_tier), []
    ) == ["p_only_core"]
