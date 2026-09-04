import logging
from sqlalchemy.orm import Session
from models.help import HelpContextHint

logger = logging.getLogger(__name__)

# Structure only — the texts live in the frontend's translation.json under
# `help.hints.*`, like every other string in the product. They used to sit in
# four hint_text_* columns here, which made this the one help surface whose
# language the server picked; switching the language left the hint stale until
# a reload. Same move e43b3ed made for the tour (TF-625/TF-670).
#
# The key is explicit rather than derived from route_pattern so that renaming a
# route does not silently detach its text.
DEFAULT_HINTS = [
    # Route patterns are matched with `startswith` against the visited path
    # (help_context_service). Two of these pointed at paths this app has never
    # had — "/documents/upload" (upload lives on /documents) and "/exam/create"
    # (it is /questions/generate) — so the two hints carrying the only
    # genuinely non-obvious advice could never fire, while filler ones did.
    {
        "route_pattern": "/documents",
        "role": "teacher",
        "i18n_key": "help.hints.documents",
        "priority": 10,
    },
    {
        "route_pattern": "/questions/generate",
        "role": "teacher",
        "i18n_key": "help.hints.questionsGenerate",
        "priority": 10,
    },
    {
        "route_pattern": "/prompts",
        "role": None,  # Visible for all roles (teacher + admin)
        "i18n_key": "help.hints.prompts",
        "priority": 10,
    },
    # The next two used to restate their own page title ("review questions" on
    # the review page). Rewritten to point at something the page does not say
    # by itself — the filters, and where the composer's questions come from.
    {
        "route_pattern": "/questions/review",
        "role": "teacher",
        "i18n_key": "help.hints.questionsReview",
        "priority": 5,
    },
    {
        "route_pattern": "/exams/compose",
        "role": "teacher",
        "i18n_key": "help.hints.examsCompose",
        "priority": 5,
    },
]

_UPSERT_FIELDS = ("role", "i18n_key", "priority")


# Patterns that were corrected or dropped above. The upsert keys on
# route_pattern, so fixing a pattern inserts a new row and leaves the old one
# behind — dead but present, and it would reappear in every environment that
# ran the old seed.
#
# "/admin/users" never existed as a route: the user management is a tab in
# React state under "/admin" (Admin.tsx), and the path only appears in
# routes/AppRoutes.example.tsx, which nothing imports. The hint therefore never
# fired once. Dropped rather than re-pointed at "/admin": the admin tour walks
# that page in two deep-dive tracks, so a hint there adds nothing.
OBSOLETE_ROUTE_PATTERNS = ("/documents/upload", "/exam/create", "/admin/users")


def seed_help_hints(db: Session) -> int:
    created = 0
    updated = 0
    removed = (
        db.query(HelpContextHint)
        .filter(HelpContextHint.route_pattern.in_(OBSOLETE_ROUTE_PATTERNS))
        .delete(synchronize_session=False)
    )
    if removed:
        logger.info("Removed %d obsolete help hint(s)", removed)
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

    # `removed` belongs in this condition: without it a run that only deletes
    # obsolete rows commits nothing and the delete is rolled back on close.
    if created > 0 or updated > 0 or removed > 0:
        db.commit()
        logger.info(
            f"Help context hints: {created} created, {updated} updated, "
            f"{removed} removed."
        )
    else:
        logger.info("Help context hints already up to date, skipping.")

    return created + updated
