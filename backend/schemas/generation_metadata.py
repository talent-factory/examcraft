"""Provenance-Snapshot der Vorlage, mit der eine Frage generiert wurde (TF-383).

Ein einziges, geteiltes Envelope-Modell statt vierfach duplizierter dict-Shapes
(SQLAlchemy-JSON-Spalte, Premium-Dataclass, zwei API-Responses, TS-Interface).
Liegt bewusst in ``core`` (OSS): premium darf core importieren, core nicht
premium — so können beide Tiers dieselbe Form benutzen und validieren.

Der ``variables``-Payload bleibt absichtlich offen (``Dict[str, Any]``), da seine
Schlüssel template-/benutzergetrieben sind. Nur die *Hülle* ist ein festes Schema.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class GenerationMetadata(BaseModel):
    """Welche Vorlage/Variablen erzeugten eine Frage — eingefroren zum
    Generierungszeitpunkt (Snapshot, kein Live-Verweis).

    Drei ehrliche Zustände, am ``is_default_template`` / ``fallback_to_default``
    ablesbar:

    * **default**  — ``is_default_template=True``, ``fallback_to_default=False``,
      ``prompt_id=None`` (hartkodiertes Standard-Template wurde verwendet).
    * **custom**   — ``is_default_template=False``, ``prompt_id`` gesetzt,
      ``prompt_name``/``prompt_version`` aus der Knowledge Base.
    * **fallback** — ``is_default_template=True``, ``fallback_to_default=True``,
      ``prompt_id`` (angefragt) bleibt erhalten: ein Custom-Render schlug fehl und
      fiel aufs Standard-Template zurück.
    """

    prompt_id: Optional[str] = None
    # None möglich, wenn das Prompt-Objekt beim Re-Lookup verschwand (Race/
    # gelöscht); prompt_id bleibt in dem Fall trotzdem erhalten.
    prompt_name: Optional[str] = None
    prompt_version: Optional[int] = None
    is_default_template: bool = True
    # Immer präsent (Default False), damit der Drei-Zustand ehrlich abbildbar ist
    # und Konsumenten nicht zwischen "False" und "Schlüssel fehlt" raten müssen.
    fallback_to_default: bool = False
    variables: Dict[str, Any] = Field(default_factory=dict)
