"""Provenance-Snapshot der Vorlage, mit der eine Frage generiert wurde (TF-383).

Ein einziges, geteiltes Envelope-Modell statt vierfach duplizierter dict-Shapes
(SQLAlchemy-JSON-Spalte, Premium-Dataclass, zwei API-Responses, TS-Interface).
Liegt bewusst in ``core`` (OSS): premium darf core importieren, core nicht
premium — so können beide Tiers dieselbe Form benutzen und validieren.

Der ``variables``-Payload bleibt absichtlich offen (``Dict[str, Any]``), da seine
Schlüssel template-/benutzergetrieben sind. Nur die *Hülle* ist ein festes Schema.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    # Snapshot = unveränderlich nach Konstruktion (eingefroren zum
    # Generierungszeitpunkt). Erzwingt die "kein Live-Verweis"-Zusage des Typs.
    model_config = ConfigDict(frozen=True)

    prompt_id: Optional[str] = None
    # None möglich, wenn das Prompt-Objekt beim Re-Lookup verschwand (Race/
    # gelöscht); prompt_id bleibt in dem Fall trotzdem erhalten.
    prompt_name: Optional[str] = None
    prompt_version: Optional[int] = Field(default=None, ge=1)
    is_default_template: bool = True
    # Immer präsent (Default False), damit der Drei-Zustand ehrlich abbildbar ist
    # und Konsumenten nicht zwischen "False" und "Schlüssel fehlt" raten müssen.
    fallback_to_default: bool = False
    variables: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_provenance_consistency(self) -> "GenerationMetadata":
        """Erzwingt die im Docstring beschriebene Zustandsmaschine, damit
        widersprüchliche Snapshots (z. B. custom ohne ``prompt_id``) gar nicht
        erst konstruierbar sind. Der Legacy-Zustand "nicht erfasst" ist davon
        unberührt — er ist das ganze Envelope ``None`` (Spalte NULL), nicht eine
        Instanz mit Defaults.
        """
        if not self.is_default_template and self.prompt_id is None:
            raise ValueError("custom provenance requires prompt_id")
        if self.fallback_to_default and not self.is_default_template:
            raise ValueError("fallback_to_default implies is_default_template=True")
        if self.fallback_to_default and self.prompt_id is None:
            raise ValueError("fallback requires the originally requested prompt_id")
        return self
