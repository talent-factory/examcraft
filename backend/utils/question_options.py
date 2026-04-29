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
    * ``dict`` with single-letter keys (``'A'/'B'/'C'/'D'``) → values
      ordered by sorted key. Logged at WARNING — this branch only fires on
      the legacy shape the data migration is supposed to drain; persistent
      hits mean the migration didn't run or a writer reintroduced the bug.
    * ``dict`` with non-letter keys (numeric strings ``'1','10','2'``,
      mixed shapes, …) → ``None`` and logged at ERROR. Lex-sorting numeric
      keys silently reorders answers (``'1','10','2'`` → answer at
      original position 2 ends up rendered between positions 1 and 10).
      The TF-330 migration explicitly leaves numeric-key rows untouched
      because the original positional intent can't be reconstructed; the
      read path follows suit.
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
        keys = list(value.keys())
        # Defensive: numeric/mixed keys can't be lex-sorted into the original
        # positional order. TF-330 migration leaves them alone for the same
        # reason — surface as ERROR so the corruption is visible.
        if not all(isinstance(k, str) and len(k) == 1 and k.isalpha() for k in keys):
            logger.error(
                "question_options.unsafe_dict_keys keys=%s — refusing to lex-sort",
                sorted(str(k) for k in keys),
            )
            return None
        logger.warning(
            "question_options.legacy_dict_shape keys=%s",
            sorted(str(k) for k in keys),
        )
        return [str(value[key]) for key in sorted(keys)]
    logger.error(
        "question_options.unsupported_type type=%s repr=%r",
        type(value).__name__,
        value,
    )
    return None
