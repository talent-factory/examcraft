"""Tests für das GenerationMetadata-Envelope (TF-383).

Sichert die drei ehrlichen Zustände (default/custom/fallback), die immer
präsente fallback_to_default-Flag, den offenen variables-Payload und die
bewusst nachsichtige Read-Validierung (kein 500 bei Teil-/Altdaten).
"""

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
    zurück statt ein 500 zu werfen. Bewusste Entscheidung gegen strikte
    Validierung auf dem Read-Pfad."""
    gm = GenerationMetadata.model_validate(
        {"prompt_id": "u1", "is_default_template": False}
    )
    assert gm.prompt_name is None
    assert gm.prompt_version is None
    assert gm.fallback_to_default is False
    assert gm.variables == {}
