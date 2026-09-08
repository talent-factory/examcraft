"""Schlüsselparität der vier Backend-Locales (TF-773 Teil C).

Das Gate aus TF-670 deckt nur ``core/frontend/src/locales/`` ab. Für die
Backend-Locales gab es keines — und dieselbe Lücke, die TF-670 im Frontend
gerade geschlossen hat, läuft hier sonst erneut auf: ``translation_service.t()``
konfiguriert ``fallback=de``, ein in fr fehlender Schlüssel liefert also
*deutschen* Text an französischsprachige Nutzer statt eines sichtbaren Fehlers.

Bewusst ein pytest-Test und kein eigener CI-Schritt: die Backend-Suite läuft in
CI ohnehin, und TF-772 Teil C3 verlangt ausdrücklich, dass kein Gate doppelt
(in ci.yml *und* im Testlauf) verdrahtet ist.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from services.translation_service import SUPPORTED_LOCALES

LOCALES_DIR = pathlib.Path(__file__).resolve().parents[1] / "locales"


def _load(lang: str) -> dict[str, str]:
    doc = json.loads((LOCALES_DIR / f"t.{lang}.json").read_text(encoding="utf-8"))
    # Die Dateien sind unter dem Sprachcode verschachtelt: {"de": {...}}.
    # Auf oberster Ebene zu zählen ergibt 1 und sieht wie eine leere Datei aus.
    assert list(doc.keys()) == [lang], (
        f"t.{lang}.json muss genau einen Top-Level-Schlüssel '{lang}' haben, "
        f"gefunden: {list(doc.keys())}"
    )
    return doc[lang]


def test_alle_vier_locales_existieren():
    for lang in SUPPORTED_LOCALES:
        assert (LOCALES_DIR / f"t.{lang}.json").is_file(), f"t.{lang}.json fehlt"


@pytest.mark.parametrize("lang", [t for t in SUPPORTED_LOCALES if t != "de"])
def test_schluesselparitaet_gegen_de(lang: str):
    de = set(_load("de"))
    other = set(_load(lang))

    missing = sorted(de - other)
    extra = sorted(other - de)

    assert not missing, (
        f"t.{lang}.json fehlen {len(missing)} Schlüssel gegenüber de: {missing}. "
        f"Wegen fallback=de erscheint dort sonst deutscher Text, nicht "
        f"der Schlüsselname — der Fehler ist im UI unsichtbar."
    )
    assert not extra, (
        f"t.{lang}.json hat {len(extra)} Schlüssel, die de nicht kennt: {extra}. "
        f"Die sind entweder verwaist oder in de vergessen worden."
    )


@pytest.mark.parametrize("lang", SUPPORTED_LOCALES)
def test_keine_leeren_werte(lang: str):
    """Ein leerer String ist schlimmer als ein fehlender Schlüssel: er umgeht
    den Fallback und rendert nichts."""
    empty = sorted(k for k, v in _load(lang).items() if not str(v).strip())
    assert not empty, f"t.{lang}.json hat leere Werte: {empty}"


@pytest.mark.parametrize("lang", [t for t in SUPPORTED_LOCALES if t != "de"])
def test_interpolationsvariablen_stimmen_ueberein(lang: str):
    """``%{name}`` muss in allen Sprachen dieselbe Variablenmenge sein.

    Eine in der Übersetzung vergessene Variable fällt sonst erst auf, wenn ein
    französischsprachiger Nutzer die Meldung ohne den eingesetzten Wert sieht;
    eine erfundene Variable lässt python-i18n den Platzhalter roh stehen.
    """
    import re

    pattern = re.compile(r"%\{(\w+)\}")
    de = _load("de")
    other = _load(lang)

    drift = {}
    for key, de_value in de.items():
        if key not in other:
            continue  # deckt test_schluesselparitaet_gegen_de ab
        de_vars = set(pattern.findall(str(de_value)))
        other_vars = set(pattern.findall(str(other[key])))
        if de_vars != other_vars:
            drift[key] = {"de": sorted(de_vars), lang: sorted(other_vars)}

    assert not drift, f"Abweichende Interpolationsvariablen in t.{lang}.json: {drift}"
