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


# ---------------------------------------------------------------------------
# TF-608: gemeinsamer Mapper Task-Exception → sichere User-Meldung.
#
# Lebt hier (statt lokal in einem einzelnen Endpoint), damit sowohl der
# WebSocket-Stream (`api/v1/websocket.py`) als auch der REST-Recovery-
# Endpoint (`GET /rag/tasks/{id}/result`, `api/rag_exams.py`) exakt dieselbe
# TF-358-Sanitisierung verwenden. Eine der beiden Stellen hat vorher
# ``str(exception)`` roh an den Client zurückgegeben — genau der Leak, den
# dieser Mapper verhindern soll.
# ---------------------------------------------------------------------------

GENERIC_TASK_ERROR = "Verarbeitung fehlgeschlagen. Bitte erneut versuchen."
"""Generische Fallback-Meldung für unbekannte Task-Fehler. Bewusst nichts-
sagend gegenüber dem User, um keine internen Details/PII zu leaken."""


def user_facing_task_error(raw_info: Any) -> str:
    """Mappe eine (technische) Task-Exception auf eine sichere, handlungs-
    leitende deutsche User-Meldung (TF-358).

    Der echte Fehler muss vom Aufrufer serverseitig geloggt werden — hier wird
    er NICHT an den User durchgereicht. Nur explizit bekannte Fehlerklassen
    erhalten eine konkrete Meldung; alles andere fällt auf eine generische
    Meldung zurück, damit keine internen Details oder personenbezogenen Daten
    zum Client gelangen.

    Matching primär über den stabilen ``code`` der RAG-Fehler oben — robust
    gegen Umformulierung/Lokalisierung. Der Substring-Fallback greift, falls
    Celery den Exception-Typ bei der Serialisierung verloren hat und nur noch
    die Roh-Message überlebt.
    """
    code = getattr(raw_info, "code", None)
    text = str(raw_info or "").lower()

    if (
        code == NO_CONTEXT
        or "no context available" in text
        or "no relevant context found" in text
    ):
        return (
            "Die ausgewählten Dokumente enthalten zu wenig durchsuchbaren "
            "Inhalt für die Fragengenerierung. Bitte zusätzliche oder "
            "umfangreichere Dokumente auswählen oder die Anzahl der Fragen "
            "reduzieren."
        )

    if code == UNKNOWN_QUESTION_TYPE or "unknown question type" in text:
        return (
            "Der gewählte Fragetyp wird nicht unterstützt. Bitte einen anderen "
            "Fragetyp auswählen."
        )

    return GENERIC_TASK_ERROR
