"""Provenance snapshot of the template a question was generated with (TF-383).

A single, shared envelope model instead of a fourfold-duplicated dict shape
(SQLAlchemy JSON column, Premium dataclass, two API responses, TS interface).
Deliberately lives in ``core`` (OSS): premium is allowed to import core, core
not premium — so both tiers can use and validate the same shape.

The ``variables`` payload is deliberately left open (``Dict[str, Any]``) since
its keys are template-/user-driven. Only the *envelope* itself is a fixed schema.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GenerationMetadata(BaseModel):
    """Which template/variables produced a question — frozen at
    generation time (a snapshot, not a live reference).

    Three honest states, readable from ``is_default_template`` /
    ``fallback_to_default``:

    * **default**  — ``is_default_template=True``, ``fallback_to_default=False``,
      ``prompt_id=None`` (the hardcoded default template was used).
    * **custom**   — ``is_default_template=False``, ``prompt_id`` set,
      ``prompt_name``/``prompt_version`` from the knowledge base.
    * **fallback** — ``is_default_template=True``, ``fallback_to_default=True``,
      ``prompt_id`` (the requested one) is retained: a custom render failed and
      fell back to the default template.
    """

    # Snapshot = immutable after construction (frozen at generation
    # time). Enforces the type's "no live reference" promise.
    model_config = ConfigDict(frozen=True)

    prompt_id: Optional[str] = None
    # None is possible if the prompt object vanished on re-lookup (race/
    # deleted); prompt_id is still retained in that case.
    prompt_name: Optional[str] = None
    prompt_version: Optional[int] = Field(default=None, ge=1)
    is_default_template: bool = True
    # Always present (default False), so the three-state model can be
    # represented honestly and consumers never have to guess between "False"
    # and "key missing".
    fallback_to_default: bool = False
    variables: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_provenance_consistency(self) -> "GenerationMetadata":
        """Enforces the state machine described in the docstring, so
        contradictory snapshots (e.g. custom without ``prompt_id``) can never
        be constructed in the first place. The legacy "not captured" state is
        unaffected by this — it's the whole envelope being ``None`` (column
        NULL), not an instance with defaults.
        """
        if not self.is_default_template and self.prompt_id is None:
            raise ValueError("custom provenance requires prompt_id")
        if self.fallback_to_default and not self.is_default_template:
            raise ValueError("fallback_to_default implies is_default_template=True")
        if self.fallback_to_default and self.prompt_id is None:
            raise ValueError("fallback requires the originally requested prompt_id")
        return self
