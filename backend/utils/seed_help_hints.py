import logging
from sqlalchemy.orm import Session
from models.help import HelpContextHint

logger = logging.getLogger(__name__)

DEFAULT_HINTS = [
    {
        "route_pattern": "/documents/upload",
        "role": "teacher",
        "hint_text_de": "Tipp: Strukturierte PDFs mit Überschriften liefern bessere Prüfungsfragen.",
        "hint_text_en": "Tip: Structured PDFs with headings produce better exam questions.",
        "priority": 10,
    },
    {
        "route_pattern": "/exam/create",
        "role": "teacher",
        "hint_text_de": "Neu hier? Wähle zuerst 3–5 Dokumente für optimale Qualität.",
        "hint_text_en": "New here? Select 3–5 documents first for optimal quality.",
        "priority": 10,
    },
    {
        "route_pattern": "/admin/users",
        "role": "admin",
        "hint_text_de": "Du kannst Benutzerrollen direkt in der Tabelle ändern.",
        "hint_text_en": "You can change user roles directly in the table.",
        "priority": 10,
    },
    {
        "route_pattern": "/prompts",
        "role": None,  # Sichtbar für alle Rollen (teacher + admin)
        "hint_text_de": "Die Live-Vorschau zeigt dir, wie der Prompt mit echten Variablen aussieht.",
        "hint_text_en": "The live preview shows you how the prompt looks with real variables.",
        "priority": 10,
    },
    {
        "route_pattern": "/questions/review",
        "role": "teacher",
        "hint_text_de": "Überprüfe generierte Fragen und bewerte sie, um die Qualität zu verbessern.",
        "hint_text_en": "Review generated questions and rate them to improve quality.",
        "priority": 5,
    },
    {
        "route_pattern": "/exams/compose",
        "role": "teacher",
        "hint_text_de": "Wähle Fragen aus der Bibliothek und stelle deine Prüfung zusammen.",
        "hint_text_en": "Select questions from the library and compose your exam.",
        "priority": 5,
    },
]

_UPSERT_FIELDS = ("role", "hint_text_de", "hint_text_en", "priority")


def seed_help_hints(db: Session) -> int:
    created = 0
    updated = 0
    for hint_data in DEFAULT_HINTS:
        existing = (
            db.query(HelpContextHint)
            .filter(HelpContextHint.route_pattern == hint_data["route_pattern"])
            .first()
        )
        if existing is None:
            hint = HelpContextHint(**hint_data, active=True)
            db.add(hint)
            created += 1
        else:
            changed = False
            for field in _UPSERT_FIELDS:
                if getattr(existing, field) != hint_data.get(field):
                    setattr(existing, field, hint_data.get(field))
                    changed = True
            if changed:
                updated += 1

    if created > 0 or updated > 0:
        db.commit()
        logger.info(f"Help context hints: {created} created, {updated} updated.")
    else:
        logger.info("Help context hints already up to date, skipping.")

    return created + updated
