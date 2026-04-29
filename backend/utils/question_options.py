"""Helpers for QuestionReview.options shape normalization.

Historically, generated questions were persisted with two different shapes for
``options``:

* the canonical ``List[str]`` (newer RAG path), and
* a legacy ``Dict[str, str]`` keyed by ``'A'/'B'/'C'/'D'`` (older records and
  one specific generation path).

The Pydantic response schema (``ReviewQueueResponse``) only accepts the list
shape, so legacy dict-shaped rows surfaced through ``GET /question-review/queue``
crashed with a 500. ``normalize_options`` makes both shapes safe by collapsing
dicts to a sorted-by-key list.
"""

import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


def normalize_options(value: Any) -> Optional[List[str]]:
    """Normalize ``options`` to ``List[str] | None``.

    * ``None`` → ``None``.
    * ``list`` → returned with each entry coerced to ``str``.
    * ``dict`` → values ordered by sorted keys (so ``'A'/'B'/'C'/'D'`` keeps
      its natural order). Logged at WARNING — this branch only fires on the
      legacy shape the data migration is supposed to drain; persistent hits
      mean the migration didn't run or a writer reintroduced the bug.
    * any other type → ``None`` and logged at ERROR. The defensive ``None``
      keeps a corrupt row from crashing the read path, but masking it
      silently would hide a real data-corruption bug class (e.g. legacy
      double-encoded JSON strings) — surface it loudly instead.
    """
    if value is None:
        return None
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, dict):
        logger.warning(
            "question_options.legacy_dict_shape keys=%s",
            sorted(str(k) for k in value.keys()),
        )
        return [str(value[key]) for key in sorted(value.keys())]
    logger.error(
        "question_options.unsupported_type type=%s repr=%r",
        type(value).__name__,
        value,
    )
    return None
