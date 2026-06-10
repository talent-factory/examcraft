"""TF-397: canonical normalization for prompt-tag names.

Prompt-template tags used to be free-text, so separator variants of the same
concept accumulated (``multiple_choice`` vs ``multiple-choice`` vs
``Multiple Choice``). Normalizing to a single canonical form lets those variants
collapse onto one managed ``Tag`` row.

Rule: trim → lowercase → collapse runs of ``-`` or whitespace to a single ``_``.

IMPORTANT: the tf397 Alembic migration backfill mirrors this exact rule in SQL
(``lower(regexp_replace(btrim(tag), '[-\\s]+', '_', 'g'))``; ``btrim`` is
Postgres' default-whitespace ``trim``). Keep the two in sync.
"""

import re

_SEPARATORS = re.compile(r"[-\s]+")


def normalize_prompt_tag_name(name: str) -> str:
    """Return the canonical form of a prompt-tag name.

    >>> normalize_prompt_tag_name("Multiple Choice")
    'multiple_choice'
    >>> normalize_prompt_tag_name("multiple-choice")
    'multiple_choice'
    >>> normalize_prompt_tag_name("  default ")
    'default'
    """
    return _SEPARATORS.sub("_", name.strip().lower())
