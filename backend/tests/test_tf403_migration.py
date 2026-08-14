"""TF-403 migration test — verify the question_type rename against real Postgres.

The migration (``2026_06_12_tf403_qtype_rename.py``) renames the legacy
single-answer ``'multiple_choice'`` rows to ``'single_choice'`` so the freed
name can be reused for the new multi-answer type. It runs in production via
AUTO_MIGRATE=true and touches every ``question_reviews`` row, so the SQL has to
be exactly right — hence this test.

Asserts the invariants the migration promises:

1. ``question_reviews`` rows with ``'multiple_choice'`` flip to
   ``'single_choice'``; ``'true_false'`` / ``'open_ended'`` rows are untouched.
2. Re-running the upgrade is a no-op (idempotent — relevant under AUTO_MIGRATE).
3. ``downgrade()`` reverses a fresh upgrade.
4. ``downgrade()`` is ONE-WAY-LOSSY once genuine multi-answer ``multiple_choice``
   rows exist: it merges them with the renamed single-answer rows. This is
   documented behaviour, asserted here so the foot-gun is explicit.
5. (premium-only, skipped when the ``prompts`` table is absent) the guarded
   ``prompts.use_case`` / ``prompts.tags`` rewrites flip correctly.

Uses the ``test_db`` fixture, which rolls back each test inside a transaction,
so test rows never leak into the shared schema-init state.
"""

import importlib.util
import uuid
from pathlib import Path

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text

# Same statements as core/backend/alembic/versions/2026_06_12_tf403_qtype_rename.py.
# Kept inline rather than imported because Alembic's op.execute is bound to the
# migration runtime — this test exercises the SQL itself.
_TF403_QR_UPGRADE_SQL = (
    "UPDATE question_reviews SET question_type = 'single_choice' "
    "WHERE question_type = 'multiple_choice'"
)
_TF403_QR_DOWNGRADE_SQL = (
    "UPDATE question_reviews SET question_type = 'multiple_choice' "
    "WHERE question_type = 'single_choice'"
)
_TF403_PROMPTS_USECASE_SQL = (
    "UPDATE prompts SET use_case = 'question_generation_single_choice' "
    "WHERE use_case = 'question_generation_multiple_choice'"
)
_TF403_PROMPTS_TAGS_SQL = (
    "UPDATE prompts SET tags = array_replace(tags, 'multiple_choice', 'single_choice') "
    "WHERE 'multiple_choice' = ANY(tags)"
)


def _seed_user_and_institution(test_db, *, user_id: int = 40398) -> None:
    """question_reviews.created_by FKs users.id, users.institution_id FKs
    institutions.id. Seed both via the ORM so we don't enumerate every NOT NULL
    column as the schema evolves."""
    from models.auth import Institution, User

    institution = Institution(
        id=40399,
        name="TF403 Test Institution",
        slug=f"tf403-{user_id}",
    )
    test_db.merge(institution)
    user = User(
        id=user_id,
        email=f"tf403-test-{user_id}@example.test",
        first_name="TF403",
        last_name="Test",
        institution_id=40399,
    )
    test_db.merge(user)
    test_db.flush()


def _insert_review(
    test_db, *, review_id: int, question_type: str, user_id: int = 40398
) -> None:
    """Insert a minimal QuestionReview row with the given question_type."""
    test_db.execute(
        text(
            """
            INSERT INTO question_reviews (
                id, question_text, question_type, options, correct_answer,
                difficulty, topic, language, source_chunks, source_documents,
                confidence_score, review_status, exam_id, created_by, created_at,
                institution_id
            )
            VALUES (
                :id, :question_text, :question_type, NULL, :correct_answer,
                :difficulty, :topic, :language,
                CAST(:source_chunks AS jsonb), CAST(:source_documents AS jsonb),
                :confidence_score, :review_status, :exam_id, :created_by, NOW(),
                :institution_id
            )
            """
        ),
        {
            "id": review_id,
            "question_text": f"TF403 question {review_id}",
            "question_type": question_type,
            "correct_answer": "A",
            "difficulty": "medium",
            "topic": "tf403-migration-test",
            "language": "de",
            "source_chunks": "[]",
            "source_documents": "[]",
            "confidence_score": 0.9,
            "review_status": "pending",
            "exam_id": "exam-tf403",
            "created_by": user_id,
            # TF-642: default visibility='institution' requires institution_id.
            "institution_id": 40399,
        },
    )


def _qtype(test_db, review_id: int) -> str | None:
    row = test_db.execute(
        text("SELECT question_type FROM question_reviews WHERE id = :id"),
        {"id": review_id},
    ).fetchone()
    return row[0] if row is not None else None


@pytest.fixture
def seeded_reviews(test_db):
    """One row of each pre-rename type."""
    _seed_user_and_institution(test_db)
    _insert_review(test_db, review_id=40301, question_type="multiple_choice")
    _insert_review(test_db, review_id=40302, question_type="true_false")
    _insert_review(test_db, review_id=40303, question_type="open_ended")
    test_db.flush()
    yield test_db


def test_upgrade_renames_only_multiple_choice(seeded_reviews):
    seeded_reviews.execute(text(_TF403_QR_UPGRADE_SQL))
    seeded_reviews.flush()

    assert _qtype(seeded_reviews, 40301) == "single_choice"  # renamed
    assert _qtype(seeded_reviews, 40302) == "true_false"  # untouched
    assert _qtype(seeded_reviews, 40303) == "open_ended"  # untouched


def test_upgrade_is_idempotent(seeded_reviews):
    """AUTO_MIGRATE=true re-runs until Alembic stamps the rev; after the first
    pass no 'multiple_choice' rows remain so a second pass is a no-op."""
    seeded_reviews.execute(text(_TF403_QR_UPGRADE_SQL))
    seeded_reviews.flush()
    first = _qtype(seeded_reviews, 40301)

    seeded_reviews.execute(text(_TF403_QR_UPGRADE_SQL))
    seeded_reviews.flush()

    assert first == "single_choice"
    assert _qtype(seeded_reviews, 40301) == "single_choice"


def test_downgrade_reverses_fresh_upgrade(seeded_reviews):
    seeded_reviews.execute(text(_TF403_QR_UPGRADE_SQL))
    seeded_reviews.flush()
    seeded_reviews.execute(text(_TF403_QR_DOWNGRADE_SQL))
    seeded_reviews.flush()

    assert _qtype(seeded_reviews, 40301) == "multiple_choice"
    assert _qtype(seeded_reviews, 40302) == "true_false"


def test_downgrade_is_lossy_once_multi_answer_rows_exist(seeded_reviews):
    """Documents the known foot-gun: after the application phase authors genuine
    multi-answer 'multiple_choice' rows, downgrade() folds the renamed
    single_choice rows back into 'multiple_choice', making the two
    indistinguishable. Both rows below end up 'multiple_choice'."""
    # 40301 is a renamed single-answer row (now single_choice after upgrade).
    seeded_reviews.execute(text(_TF403_QR_UPGRADE_SQL))
    seeded_reviews.flush()
    # 40304 is a genuine multi-answer row authored after the rename.
    _insert_review(seeded_reviews, review_id=40304, question_type="multiple_choice")
    seeded_reviews.flush()

    seeded_reviews.execute(text(_TF403_QR_DOWNGRADE_SQL))
    seeded_reviews.flush()

    # Single-answer (renamed) and multi-answer rows are now both multiple_choice.
    assert _qtype(seeded_reviews, 40301) == "multiple_choice"
    assert _qtype(seeded_reviews, 40304) == "multiple_choice"


def test_prompts_use_case_and_tags_renamed_when_table_present(test_db):
    """Premium-only branch: the migration guards the prompts UPDATEs on the
    table existing (created via create_all only when premium is mounted). When
    present, use_case and the legacy tags array flip; in core deployments the
    table is absent and this is a clean skip (mirrors the migration's guard)."""
    if "prompts" not in set(sa_inspect(test_db.get_bind()).get_table_names()):
        pytest.skip("prompts is premium-only; absent in the core schema")

    pid = str(uuid.uuid4())
    test_db.execute(
        text(
            """
            INSERT INTO prompts (id, name, content, category, use_case, tags, version)
            VALUES (CAST(:id AS uuid), :name, :content, :category, :use_case,
                    CAST(:tags AS text[]), 1)
            """
        ),
        {
            "id": pid,
            "name": f"tf403-prompt-{pid}",
            "content": "x",
            "category": "question_generation",
            "use_case": "question_generation_multiple_choice",
            "tags": "{multiple_choice,other_tag}",
        },
    )
    test_db.flush()

    test_db.execute(text(_TF403_PROMPTS_USECASE_SQL))
    test_db.execute(text(_TF403_PROMPTS_TAGS_SQL))
    test_db.flush()

    row = test_db.execute(
        text("SELECT use_case, tags FROM prompts WHERE id = CAST(:id AS uuid)"),
        {"id": pid},
    ).fetchone()
    assert row[0] == "question_generation_single_choice"
    assert "single_choice" in row[1]
    assert "multiple_choice" not in row[1]
    assert "other_tag" in row[1]  # unrelated tags preserved


def test_migration_revision_chain_and_id_limit():
    """alembic_version.version_num is VARCHAR(32) so the revision id must fit,
    and the down_revision must chain onto the develop head it was branched from
    (guards against a stale parent after a develop merge)."""
    mig_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "2026_06_12_tf403_qtype_rename.py"
    )
    spec = importlib.util.spec_from_file_location("tf403_qtype_rename_mig", mig_path)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)

    assert len(mig.revision) <= 32
    assert mig.revision == "tf403_qtype_rename"
    # Re-parented onto tf346 (develop merge) to keep a single linear head.
    assert mig.down_revision == "tf346_prompt_institution"
