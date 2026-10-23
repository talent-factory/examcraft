"""
Rewrite open_ended questions whose correct_answer/explanation was stored as a raw
JSON model answer or rubric into the readable Markdown that new generations get.

Only ``open_ended`` rows are touched: ``multiple_choice`` answers are a JSON
array by design (DeterministicGrader parses them). Plain text and JSON that is
not a model answer/rubric are left as they are (see
``services.structured_text``). Rows stored as a Python repr (``{'a': ...}``) are
not valid JSON and are not fixed.

The questions must be named explicitly with ``--ids``. Without ``--apply`` the
script only prints the old and new value of every field it would change. With
``--apply`` each change is written together with a ``review_history`` entry
holding the old and new values, so it can be reverted.

Usage (inside the backend container):

    python scripts/flatten_structured_answers.py --ids 1 2 3 [--apply]
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("flatten_structured_answers")

FIELDS = ("correct_answer", "explanation")
CHANGED_BY = "script:flatten_structured_answers"


def flatten(ids: list[int], apply: bool) -> int:
    from database import SessionLocal
    from models.question_review import QuestionReview, ReviewHistory
    from services.structured_text import structured_to_markdown

    db = SessionLocal()
    try:
        questions = (
            db.query(QuestionReview)
            .filter(QuestionReview.id.in_(ids))
            .order_by(QuestionReview.id)
            .all()
        )
        found = {question.id for question in questions}
        missing = sorted(set(ids) - found)
        if missing:
            logger.error("IDs not found: %s", missing)
        skipped = [q.id for q in questions if q.question_type != "open_ended"]
        if skipped:
            logger.error("IDs that are not open_ended (not touched): %s", skipped)

        changed = 0
        for question in questions:
            if question.question_type != "open_ended":
                continue
            updates = {}
            for field in FIELDS:
                value = getattr(question, field)
                rendered = structured_to_markdown(value)
                if rendered != value:
                    updates[field] = {"old": value, "new": rendered}
            if not updates:
                logger.info("id=%s: nothing to change", question.id)
                continue
            changed += 1
            logger.info("id=%s status=%s", question.id, question.review_status)
            for field, change in updates.items():
                logger.info(
                    "  %s\n    old: %r\n    new: %r",
                    field,
                    change["old"],
                    change["new"],
                )
                setattr(question, field, change["new"])
            db.add(
                ReviewHistory(
                    question_id=question.id,
                    action="edited",
                    old_status=question.review_status,
                    new_status=question.review_status,
                    changed_fields=updates,
                    changed_by=CHANGED_BY,
                    change_reason="Structured JSON answer rendered as Markdown",
                )
            )

        exit_code = 1 if missing or skipped else 0
        if not apply:
            db.rollback()
            logger.info("Dry-run: %d question(s) would be rewritten.", changed)
            return exit_code
        db.commit()
        logger.info("Rewrote %d question(s).", changed)
        return exit_code
    except Exception:
        db.rollback()
        logger.exception("Aborted, nothing written.")
        return 1
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ids", type=int, nargs="+", required=True, help="Question IDs to rewrite"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Write changes (default: dry-run)"
    )
    args = parser.parse_args()
    return flatten(args.ids, args.apply)


if __name__ == "__main__":
    sys.exit(main())
