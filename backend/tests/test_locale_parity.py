"""Schlüsselparität der vier Backend-Locales (TF-773 Teil C).

Das Gate aus TF-670 deckt nur ``core/frontend/src/locales/`` ab. Für die
Backend-Locales gab es keines — und dieselbe Lücke, die TF-670 im Frontend
gerade geschlossen hat, läuft hier sonst erneut auf: ``translation_service.t()``
konfiguriert ``fallback=de``, ein in fr fehlender Schlüssel liefert also
*deutschen* Text an französischsprachige Nutzer statt eines sichtbaren Fehlers.

Bewusst ein pytest-Test und kein eigener CI-Schritt: die Backend-Suite läuft in
CI ohnehin, und TF-772 Teil C3 verlangt ausdrücklich, dass kein Gate doppelt
(in ci.yml *und* im Testlauf) verdrahtet ist.

Seit TF-773 PR 2b gibt es mehr als ein Locale-Verzeichnis: ``premium/backend/
locales/`` liegt neben dem aus Core (ADR 0006). Jede Prüfung läuft pro
Verzeichnis; dazu kommt die Disjunktheit über alle Verzeichnisse, weil
python-i18n einen doppelten Schlüssel still vom zuletzt registrierten
Verzeichnis gewinnen lässt. Fehlende Tier-Verzeichnisse werden übersprungen —
im ``core/``-Mirror gibt es nur das aus Core.
"""

from __future__ import annotations

import itertools
import json
import pathlib
import re

import pytest

from services.translation_service import SUPPORTED_LOCALES

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CORE_LOCALES_DIR = pathlib.Path(__file__).resolve().parents[1] / "locales"


def _locale_dirs() -> dict[str, pathlib.Path]:
    """Tier-Name → Locale-Verzeichnis, nur für vorhandene Verzeichnisse."""
    dirs = {"core": CORE_LOCALES_DIR}
    for tier in ("premium", "enterprise"):
        candidate = REPO_ROOT / tier / "backend" / "locales"
        if candidate.is_dir():
            dirs[tier] = candidate
    return dirs


LOCALE_DIRS = _locale_dirs()
_NON_DE = [lang for lang in SUPPORTED_LOCALES if lang != "de"]


def _load(tier: str, lang: str) -> dict[str, str]:
    path = LOCALE_DIRS[tier] / f"t.{lang}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    # Die Dateien sind unter dem Sprachcode verschachtelt: {"de": {...}}.
    # Auf oberster Ebene zu zählen ergibt 1 und sieht wie eine leere Datei aus.
    assert list(doc.keys()) == [lang], (
        f"{tier}: t.{lang}.json muss genau einen Top-Level-Schlüssel '{lang}' "
        f"haben, gefunden: {list(doc.keys())}"
    )
    return doc[lang]


def _params(langs):
    return [
        pytest.param(tier, lang, id=f"{tier}-{lang}")
        for tier in LOCALE_DIRS
        for lang in langs
    ]


def test_core_verzeichnis_wird_gefunden():
    """Sanity-Check: ein verschobenes Core-Verzeichnis darf nicht dazu führen,
    dass alle parametrisierten Tests mangels Parametern still grün sind."""
    assert CORE_LOCALES_DIR.is_dir()


@pytest.mark.parametrize("tier", list(LOCALE_DIRS))
def test_alle_vier_locales_existieren(tier: str):
    for lang in SUPPORTED_LOCALES:
        assert (LOCALE_DIRS[tier] / f"t.{lang}.json").is_file(), (
            f"{tier}: t.{lang}.json fehlt"
        )


@pytest.mark.parametrize(("tier", "lang"), _params(_NON_DE))
def test_schluesselparitaet_gegen_de(tier: str, lang: str):
    de = set(_load(tier, "de"))
    other = set(_load(tier, lang))

    missing = sorted(de - other)
    extra = sorted(other - de)

    assert not missing, (
        f"{tier}: t.{lang}.json fehlen {len(missing)} Schlüssel gegenüber de: "
        f"{missing}. Wegen fallback=de erscheint dort sonst deutscher Text, "
        f"nicht der Schlüsselname — der Fehler ist im UI unsichtbar."
    )
    assert not extra, (
        f"{tier}: t.{lang}.json hat {len(extra)} Schlüssel, die de nicht kennt: "
        f"{extra}. Die sind entweder verwaist oder in de vergessen worden."
    )


@pytest.mark.parametrize(("tier", "lang"), _params(SUPPORTED_LOCALES))
def test_keine_leeren_werte(tier: str, lang: str):
    """Ein leerer String ist schlimmer als ein fehlender Schlüssel: er umgeht
    den Fallback und rendert nichts."""
    empty = sorted(k for k, v in _load(tier, lang).items() if not str(v).strip())
    assert not empty, f"{tier}: t.{lang}.json hat leere Werte: {empty}"


@pytest.mark.parametrize(("tier", "lang"), _params(_NON_DE))
def test_interpolationsvariablen_stimmen_ueberein(tier: str, lang: str):
    """``%{name}`` muss in allen Sprachen dieselbe Variablenmenge sein.

    Eine in der Übersetzung vergessene Variable fällt sonst erst auf, wenn ein
    französischsprachiger Nutzer die Meldung ohne den eingesetzten Wert sieht;
    eine erfundene Variable lässt python-i18n den Platzhalter roh stehen.
    """
    pattern = re.compile(r"%\{(\w+)\}")
    de = _load(tier, "de")
    other = _load(tier, lang)

    drift = {}
    for key, de_value in de.items():
        if key not in other:
            continue  # deckt test_schluesselparitaet_gegen_de ab
        de_vars = set(pattern.findall(str(de_value)))
        other_vars = set(pattern.findall(str(other[key])))
        if de_vars != other_vars:
            drift[key] = {"de": sorted(de_vars), lang: sorted(other_vars)}

    assert not drift, (
        f"{tier}: abweichende Interpolationsvariablen in t.{lang}.json: {drift}"
    )


def test_tier_schluessel_sind_disjunkt():
    """Kein Schlüssel in zwei Locale-Verzeichnissen (ADR 0006).

    python-i18n kennt zwischen Verzeichnissen keinen Vorrang, nur Reihenfolge:
    bei einem Fehltreffer lädt es die Datei aus jedem Verzeichnis und
    überschreibt. Ein doppelter Schlüssel würde also still vom zuletzt
    registrierten Verzeichnis gewinnen — je nach Registrierungsreihenfolge mit
    einem anderen Text. Geprüft wird gegen ``de``; die übrigen Sprachen ziehen
    über die Parität mit.
    """
    keys = {tier: set(_load(tier, "de")) for tier in LOCALE_DIRS}
    doppelt = {
        f"{a}/{b}": sorted(keys[a] & keys[b])
        for a, b in itertools.combinations(keys, 2)
        if keys[a] & keys[b]
    }
    assert not doppelt, (
        f"Schlüssel in mehreren Locale-Verzeichnissen: {doppelt}. Jeder "
        f"Schlüssel gehört dem Tier, dessen Code ihn wirft."
    )
