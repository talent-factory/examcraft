"""Tests for the GenerationMetadata envelope (TF-383).

Covers the three honest states (default/custom/fallback), the always-present
fallback_to_default flag, the open variables payload, and the deliberately
lenient read validation (no 500 on partial/legacy data).
"""

import pytest
from pydantic import ValidationError

from schemas.generation_metadata import GenerationMetadata


def test_default_state_flag_present_and_false():
    gm = GenerationMetadata(
        prompt_name="default_single_choice",
        is_default_template=True,
        variables={"topic": "X"},
    )
    dumped = gm.model_dump()
    assert dumped["is_default_template"] is True
    assert dumped["prompt_id"] is None
    # fallback_to_default is ALWAYS serialized (no "False vs. missing" guessing).
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
    """Read robustness: a partial dict (e.g. legacy data) falls back to
    defaults instead of raising a 500. The consistency validator only
    forbids *contradictory* states, not filling in missing fields — this
    partial dict is a valid custom state (prompt_id present)."""
    gm = GenerationMetadata.model_validate(
        {"prompt_id": "u1", "is_default_template": False}
    )
    assert gm.prompt_name is None
    assert gm.prompt_version is None
    assert gm.fallback_to_default is False
    assert gm.variables == {}


def test_custom_without_prompt_id_rejected():
    """Contradictory state: custom (is_default_template=False) without
    prompt_id cannot be constructed (TF-383 review hardening)."""
    with pytest.raises(ValidationError):
        GenerationMetadata(is_default_template=False)


def test_fallback_without_default_flag_rejected():
    """fallback_to_default implies is_default_template=True."""
    with pytest.raises(ValidationError):
        GenerationMetadata(
            prompt_id="u1", is_default_template=False, fallback_to_default=True
        )


def test_negative_prompt_version_rejected():
    """Versions must be positive (ge=1)."""
    with pytest.raises(ValidationError):
        GenerationMetadata(prompt_id="u1", is_default_template=False, prompt_version=0)


def test_snapshot_is_frozen():
    """Snapshot is immutable after construction (frozen)."""
    gm = GenerationMetadata(prompt_id="u1", is_default_template=False)
    with pytest.raises(ValidationError):
        gm.prompt_id = "u2"
