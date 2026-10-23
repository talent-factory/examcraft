"""Render structured LLM output as readable Markdown.

Custom prompts for open-ended questions often ask for a structured model answer
(structure, key points, model answer) and a scoring rubric. Depending on the
run, the model returns these as prose, as a nested object, or as a JSON string
inside a text field. Without normalisation the JSON text lands raw in
``correct_answer``/``explanation`` and is unreadable in the review view.

Only values that look like a model answer or rubric are converted. Any other
JSON (e.g. the answer to "write a JSON object for a customer") is a legitimate
answer and stays untouched.

Known limitation: the rendered headings ("Kernpunkte", "Punkte", ...) are always
German, regardless of the exam language.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Known keys -> heading. Unknown keys get a heading derived from the key name,
# so their content is rendered, not dropped.
_LABELS = {
    "structure": "Empfohlene Struktur",
    "key_points": "Kernpunkte",
    "model_answer": "Musterantwort",
    "sample_answer": "Musterantwort",
    "criteria": "Bewertungskriterien",
    "evaluation_criteria": "Bewertungskriterien",
}

# Keys that mark a dict as a model answer or rubric (rather than arbitrary JSON).
_STRUCTURED_KEYS = frozenset(_LABELS) | {"total_points"}

# Keys that identify a single rubric entry and the keys its short form consumes.
_CRITERION_NAME_KEYS = ("aspect", "name", "criterion")
_CRITERION_POINTS_KEYS = ("points", "max_points")
_CRITERION_KEYS = (
    frozenset(_CRITERION_NAME_KEYS)
    | frozenset(_CRITERION_POINTS_KEYS)
    | {"description"}
)

# A whole value wrapped in a Markdown code fence, e.g. ```json\n{...}\n```.
_FENCE = re.compile(r"^```[a-zA-Z]*\s*\n(.*)\n\s*```$", re.DOTALL)


def _label(key: Any) -> str:
    key = str(key)
    return _LABELS.get(key, key.replace("_", " ").strip().capitalize())


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _looks_like_criterion(item: Any) -> bool:
    return isinstance(item, dict) and any(item.get(key) for key in _CRITERION_NAME_KEYS)


def _looks_structured(value: dict | list) -> bool:
    """True for a model answer/rubric dict or a list of rubric entries."""
    if isinstance(value, dict):
        return any(str(key) in _STRUCTURED_KEYS for key in value)
    return bool(value) and all(_looks_like_criterion(item) for item in value)


def _parse_json_container(value: str) -> dict | list | None:
    """Parse a JSON object/array from a string (optionally fenced); else None."""
    stripped = value.strip()
    fenced = _FENCE.match(stripped)
    if fenced:
        stripped = fenced.group(1).strip()
    if not stripped or stripped[0] not in "{[":
        return None
    try:
        parsed = json.loads(stripped)
    except ValueError:
        # Text that starts like JSON but does not parse stays as it is; log it
        # so a new malformed output shape doesn't go unnoticed.
        logger.warning("structured_text.unparsed_json_like length=%d", len(value))
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def _criterion_line(item: dict) -> str | None:
    """Render a rubric entry as one line.

    Accepts ``aspect``/``name``/``criterion`` as the name, with optional
    ``points`` (or ``max_points``) and ``description``. Any further keys
    (``indicators``, ``levels``, ...) are appended so no scoring detail is lost.
    """
    aspect = next((item[key] for key in _CRITERION_NAME_KEYS if item.get(key)), None)
    if not aspect:
        return None
    points = next(
        (item[key] for key in _CRITERION_POINTS_KEYS if not _is_empty(item.get(key))),
        None,
    )
    line = f"**{_inline(aspect)}**"
    if not _is_empty(points):
        line += f" ({_inline(points)} Punkte)"
    description = item.get("description")
    if not _is_empty(description):
        line += f": {_inline(description)}"
    rest = [
        f"{_label(key)}: {_inline(value)}"
        for key, value in item.items()
        if key not in _CRITERION_KEYS and not _is_empty(value)
    ]
    if rest:
        line += " (" + "; ".join(rest) + ")"
    return line


def _list_item(item: Any) -> str:
    if isinstance(item, dict):
        line = _criterion_line(item)
        if line is not None:
            return line
        return "; ".join(
            f"{_label(k)}: {_inline(v)}" for k, v in item.items() if not _is_empty(v)
        )
    return _inline(item)


def _inline(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(_list_item(v) for v in value if not _is_empty(v))
    if isinstance(value, dict):
        return _list_item(value)
    return str(value).strip()


def _render(value: dict | list) -> str:
    if isinstance(value, list):
        return "\n".join(
            f"- {_list_item(item)}" for item in value if not _is_empty(item)
        )

    blocks: list[str] = []
    for key, item in value.items():
        if _is_empty(item):
            continue
        if key == "total_points":
            blocks.append(f"**Gesamtpunkte: {_inline(item)}**")
        elif isinstance(item, dict) and all(isinstance(v, dict) for v in item.values()):
            # Rubric keyed by criterion: {"accuracy": {"description": ..., ...}}
            lines = [
                f"- {_criterion_line({'name': _label(name), **entry})}"
                for name, entry in item.items()
            ]
            blocks.append(f"**{_label(key)}:**\n\n" + "\n".join(lines))
        elif isinstance(item, (list, dict)):
            nested = _render(item)
            if nested:
                blocks.append(f"**{_label(key)}:**\n\n{nested}")
        else:
            label = _label(key)
            text = str(item).strip()
            # The model often repeats the heading inside the value
            # ("Empfohlene Struktur: (1) ..."); don't print it twice. This only
            # matches when the model repeats the German label.
            if text.lower().startswith(f"{label.lower()}:"):
                text = text[len(label) + 1 :].lstrip()
            blocks.append(f"**{label}:**\n\n{text}")
    return "\n\n".join(blocks)


def structured_to_markdown(value: Any) -> Any:
    """Render a model answer/rubric (object or JSON string) as Markdown.

    - A JSON string is converted only if it parses to a model answer or rubric
      (see ``_looks_structured``); plain text, invalid JSON and other JSON stay
      unchanged.
    - A dict or list (which cannot be stored in a text column as is) is always
      rendered; an unrecognised shape falls back to key/value lines.
    - If nothing renders (all values empty), a string is returned unchanged and
      a dict/list becomes ``None`` instead of an empty answer.
    """
    if isinstance(value, str):
        parsed = _parse_json_container(value)
        if parsed is None or not _looks_structured(parsed):
            return value
        return _render(parsed) or value
    if isinstance(value, (dict, list)):
        return _render(value) or None
    return value
