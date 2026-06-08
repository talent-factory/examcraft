"""Tests für das GenerationMetadata-Envelope (TF-383).

Sichert die drei ehrlichen Zustände (default/custom/fallback), die immer
präsente fallback_to_default-Flag, den offenen variables-Payload und die
bewusst nachsichtige Read-Validierung (kein 500 bei Teil-/Altdaten).
"""

import pytest
from pydantic import ValidationError

from schemas.generation_metadata import GenerationMetadata


def test_default_state_flag_present_and_false():
    gm = GenerationMetadata(
        prompt_name="default_multiple_choice",
        is_default_template=True,
        variables={"topic": "X"},
    )
    dumped = gm.model_dump()
    assert dumped["is_default_template"] is True
    assert dumped["prompt_id"] is None
    # fallback_to_default ist IMMER serialisiert (kein "False vs. fehlt"-Raten).
    assert "fallback_to_default" in dumped
    assert dumped["fallback_to_default"] is False


def test_custom_state():
    gm = GenerationMetadata(
        prompt_id="u1",
        prompt_name="custom_mcq",
        prompt_version=3,
        is_default_template=False,
        variables={"topic": "X"},
    )
    assert gm.is_default_template is False
    assert gm.fallback_to_default is False
    assert gm.prompt_version == 3


def test_fallback_state_keeps_prompt_id():
    gm = GenerationMetadata(
        prompt_id="u-broken",
        prompt_name="default_open_ended",
        is_default_template=True,
        fallback_to_default=True,
    )
    assert gm.fallback_to_default is True
    assert gm.prompt_id == "u-broken"
    assert gm.variables == {}  # default_factory


def test_variables_payload_is_open():
    gm = GenerationMetadata(variables={"nested": {"a": 1}, "list": [1, 2], "s": "x"})
    assert gm.variables["nested"] == {"a": 1}
    assert gm.variables["list"] == [1, 2]


def test_stored_dict_roundtrips_unchanged():
    raw = {
        "prompt_id": "u1",
        "prompt_name": "custom_mcq",
        "prompt_version": 2,
        "is_default_template": False,
        "fallback_to_default": False,
        "variables": {"topic": "X"},
    }
    assert GenerationMetadata.model_validate(raw).model_dump() == raw


def test_partial_dict_fills_defaults_without_raising():
    """Read-Robustheit: ein Teil-Dict (z. B. Altbestand) fällt auf Defaults
    zurück statt ein 500 zu werfen. Der Konsistenz-Validator verbietet nur
    *widersprüchliche* Zustände, nicht das Auffüllen fehlender Felder — dieses
    Teil-Dict ist ein gültiger custom-Zustand (prompt_id vorhanden)."""
    gm = GenerationMetadata.model_validate(
        {"prompt_id": "u1", "is_default_template": False}
    )
    assert gm.prompt_name is None
    assert gm.prompt_version is None
    assert gm.fallback_to_default is False
    assert gm.variables == {}


def test_custom_without_prompt_id_rejected():
    """Widersprüchlicher Zustand: custom (is_default_template=False) ohne
    prompt_id ist nicht konstruierbar (TF-383-Review-Härtung)."""
    with pytest.raises(ValidationError):
        GenerationMetadata(is_default_template=False)


def test_fallback_without_default_flag_rejected():
    """fallback_to_default impliziert is_default_template=True."""
    with pytest.raises(ValidationError):
        GenerationMetadata(
            prompt_id="u1", is_default_template=False, fallback_to_default=True
        )


def test_negative_prompt_version_rejected():
    """Versionen sind positiv (ge=1)."""
    with pytest.raises(ValidationError):
        GenerationMetadata(prompt_id="u1", is_default_template=False, prompt_version=0)


def test_snapshot_is_frozen():
    """Snapshot ist nach Konstruktion unveränderlich (eingefroren)."""
    gm = GenerationMetadata(prompt_id="u1", is_default_template=False)
    with pytest.raises(ValidationError):
        gm.prompt_id = "u2"
