"""TF-330 migration test — verify the data backfill against a real Postgres DB.

The migration rewrites legacy ``{'A','B','C','D'}`` rows in
``question_reviews.options`` to ``['a','b','c','d']`` arrays. Because it runs
inside production via AUTO_MIGRATE=true and ``downgrade()`` is explicitly
``NotImplementedError``, the SQL has to be exactly right on first contact —
hence this test.

Asserts the four invariants the migration docstring promises:

1. Letter-key dicts ('A'..'D') get rewritten to a sorted list.
2. Numeric-key dicts ('1','2','3',…) are LEFT UNTOUCHED — lex-sort would
   silently reorder, and the migration is one-way.
3. ``NULL`` rows pass through unchanged.
4. Already-list rows pass through unchanged.

Uses the ``test_db`` fixture which runs everything inside a transaction the
test scaffolding rolls back, so test rows never leak into the schema-init
state shared with other tests.
"""

import json

import pytest
from sqlalchemy import text


# Same SQL as core/backend/alembic/versions/2026_04_29_tf330_normalize_options_dict_to_list.py
# Kept inline rather than imported because Alembic's `op.execute` is bound to
# the migration runtime — this test exercises the SQL itself.
_TF330_UPGRADE_SQL = """
UPDATE question_reviews
SET options = (
    SELECT jsonb_agg(value ORDER BY key)
    FROM jsonb_each_text(options::jsonb)
)
WHERE options IS NOT NULL
  AND jsonb_typeof(options::jsonb) = 'object'
  AND options::jsonb ?| array['A', 'B', 'C', 'D'];
"""


def _insert_review(test_db, *, review_id: int, options, user_id: int = 9999) -> None:
    """Insert a minimal QuestionReview row with the given options shape.

    Uses raw SQL so we can write the legacy dict shape that the SQLAlchemy
    model no longer accepts on the write path.
    """
    options_param = None if options is None else json.dumps(options)
    test_db.execute(
        text(
            """
            INSERT INTO question_reviews (
                id, question_text, question_type, options, correct_answer,
                difficulty, topic, language, source_chunks, source_documents,
                confidence_score, review_status, exam_id, created_by, created_at
            )
            VALUES (
                :id, :question_text, :question_type, CAST(:options AS jsonb),
                :correct_answer, :difficulty, :topic, :language,
                CAST(:source_chunks AS jsonb), CAST(:source_documents AS jsonb),
                :confidence_score, :review_status, :exam_id, :created_by, NOW()
            )
            """
        ),
        {
            "id": review_id,
            "question_text": f"Test question {review_id}",
            "question_type": "multiple_choice",
            "options": options_param,
            "correct_answer": "A",
            "difficulty": "medium",
            "topic": "tf330-migration-test",
            "language": "de",
            "source_chunks": "[]",
            "source_documents": "[]",
            "confidence_score": 0.9,
            "review_status": "pending",
            "exam_id": "exam-tf330",
            "created_by": user_id,
        },
    )


def _read_options(test_db, review_id: int):
    row = test_db.execute(
        text("SELECT options FROM question_reviews WHERE id = :id"),
        {"id": review_id},
    ).fetchone()
    return row[0] if row is not None else None


def _seed_user_and_institution(test_db, *, user_id: int = 9999) -> None:
    """question_reviews.created_by has a FK on users.id, users.institution_id
    has a FK on institutions.id. Seed both via the ORM so we don't have to
    enumerate every NOT NULL column manually as the schema evolves.
    """
    from models.auth import Institution, User

    institution = Institution(
        id=999,
        name="TF330 Test Institution",
        slug=f"tf330-{user_id}",
    )
    test_db.merge(institution)
    user = User(
        id=user_id,
        email=f"tf330-test-{user_id}@example.test",
        first_name="TF330",
        last_name="Test",
        institution_id=999,
    )
    test_db.merge(user)
    test_db.flush()


@pytest.fixture
def seeded_reviews(test_db):
    """Seed the four shapes the migration must handle."""
    _seed_user_and_institution(test_db)
    _insert_review(
        test_db,
        review_id=10001,
        options={
            "A": "Antwort eins",
            "B": "Antwort zwei",
            "C": "Antwort drei",
            "D": "Antwort vier",
        },
    )
    _insert_review(
        test_db,
        review_id=10002,
        options={"1": "first", "2": "second", "10": "tenth"},
    )
    _insert_review(test_db, review_id=10003, options=None)
    _insert_review(
        test_db,
        review_id=10004,
        options=["already", "a", "list"],
    )
    test_db.flush()
    yield test_db


def test_letter_key_dict_is_rewritten_to_sorted_list(seeded_reviews):
    seeded_reviews.execute(text(_TF330_UPGRADE_SQL))
    seeded_reviews.flush()

    result = _read_options(seeded_reviews, 10001)
    assert isinstance(result, list)
    assert result == [
        "Antwort eins",
        "Antwort zwei",
        "Antwort drei",
        "Antwort vier",
    ]


def test_numeric_key_dict_is_left_untouched(seeded_reviews):
    """Numeric keys ('1','2','10') would lex-sort wrong — migration filter
    on ``?| array['A','B','C','D']`` excludes them so the original dict
    stays intact and a future targeted fix can address them properly."""
    seeded_reviews.execute(text(_TF330_UPGRADE_SQL))
    seeded_reviews.flush()

    result = _read_options(seeded_reviews, 10002)
    assert isinstance(result, dict)
    assert result == {"1": "first", "2": "second", "10": "tenth"}


def test_null_options_pass_through(seeded_reviews):
    seeded_reviews.execute(text(_TF330_UPGRADE_SQL))
    seeded_reviews.flush()

    result = _read_options(seeded_reviews, 10003)
    assert result is None


def test_already_list_options_pass_through(seeded_reviews):
    seeded_reviews.execute(text(_TF330_UPGRADE_SQL))
    seeded_reviews.flush()

    result = _read_options(seeded_reviews, 10004)
    assert result == ["already", "a", "list"]


def test_idempotent_on_re_run(seeded_reviews):
    """AUTO_MIGRATE=true means the migration runs on every container start
    until Alembic stamps the rev. After the first rewrite the WHERE filter
    no longer matches the rewritten arrays, so a second run is a no-op."""
    seeded_reviews.execute(text(_TF330_UPGRADE_SQL))
    seeded_reviews.flush()
    first_pass = _read_options(seeded_reviews, 10001)

    seeded_reviews.execute(text(_TF330_UPGRADE_SQL))
    seeded_reviews.flush()
    second_pass = _read_options(seeded_reviews, 10001)

    assert first_pass == second_pass
    assert isinstance(second_pass, list)


def test_dict_without_letter_keys_left_untouched(seeded_reviews):
    """Edge case: a dict with letter keys outside A-D (e.g. all numeric or
    custom keys) must not be touched by the targeted filter."""
    _insert_review(
        seeded_reviews,
        review_id=10005,
        options={"opt_a": "x", "opt_b": "y"},
    )
    seeded_reviews.flush()

    seeded_reviews.execute(text(_TF330_UPGRADE_SQL))
    seeded_reviews.flush()

    result = _read_options(seeded_reviews, 10005)
    assert result == {"opt_a": "x", "opt_b": "y"}
