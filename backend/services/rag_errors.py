"""
Strukturierte RAG-Generierungs-Fehler mit stabilen Codes (TF-358).

Analog zu :mod:`services.document_errors`: statt rohe englische Fehlertexte
per Substring zu interpretieren, tragen die Exceptions einen stabilen,
maschinenlesbaren ``code``. Der WebSocket-Endpoint (`api/v1/websocket.py`)
mappt diesen Code auf eine sichere, handlungsleitende deutsche User-Meldung —
robust gegen Lokalisierung oder Umformulierung der Roh-Meldung.

Wichtig zur Cross-Tier-Architektur: Diese Datei lebt in ``core/`` (nicht
``premium/``), damit BEIDE Prozesse sie importieren können — der Celery-Worker
(`premium/.../rag_service.py` wirft die Exception) UND der API-Prozess
(`core/.../websocket.py` liest sie aus dem Celery-Result). Celery kann den
Exception-Typ nur dann originalgetreu rekonstruieren, wenn die Klasse in beiden
Prozessen importierbar ist; sonst degradiert sie zu einer generischen Exception
(nur die Message überlebt). Der WebSocket-Mapper hält deshalb zusätzlich einen
Substring-Fallback vor.

Codes sind stabile snake_case-Identifier — niemals lokalisieren, niemals
stillschweigend umdeuten. Neue Codes additiv ergänzen.
"""

from typing import Any, Dict

# ---------------------------------------------------------------------------
# Stabile, maschinenlesbare Fehlercodes. Additiv erweitern; nie umdeuten.
# ---------------------------------------------------------------------------

NO_CONTEXT = "no_context"
"""RAG-Retrieval lieferte keinen verwertbaren Kontext für (mind.) eine Frage
oder das gesamte Thema — die ausgewählten Dokumente sind zu kurz / nicht
indexiert."""

UNKNOWN_QUESTION_TYPE = "unknown_question_type"
"""Angeforderter Fragetyp hat kein Template / wird nicht unterstützt."""


class RAGGenerationError(ValueError):
    """ValueError-Subklasse mit stabilem ``code`` (+ optionalen ``details``).

    Erbt von ``ValueError``, damit bestehende ``except ValueError`` / Tests
    (`pytest.raises(ValueError, ...)`) unverändert greifen.

    Args:
        message: Menschenlesbare (englische) Meldung — geht in Logs/Result.
        **details: Optionale strukturierte Diagnostik (z.B. ``question_type=...``).
    """

    code: str = "rag_generation_error"

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.details: Dict[str, Any] = dict(details)


class NoContextError(RAGGenerationError):
    """Kein verwertbarer RAG-Kontext für die Fragengenerierung."""

    code = NO_CONTEXT


class UnknownQuestionTypeError(RAGGenerationError):
    """Nicht unterstützter Fragetyp."""

    code = UNKNOWN_QUESTION_TYPE
