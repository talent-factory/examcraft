"""EXAMCRAFT-192: Schema ``question_versions`` und Migration ``ec192_question_versions``.

Die Migration läuft in Prod nur auf einer bestehenden DB (frische DBs: create_all
+ stamp head). Der Migrationstest setzt deshalb in einer Transaktion den Stand
vor der Migration her (``downgrade()``), legt Altdaten an, führt ``upgrade()``
aus und rollt am Ende alles zurück (PostgreSQL-DDL ist transaktional).
"""

import importlib.util
import uuid
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from models.auth import Institution, User
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview, QuestionReviewVisibility
from models.question_version import QuestionVersion

_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "2026_11_22_ec192_question_versions.py"
)


def _question(test_db, **kw):
    q = QuestionReview(
        question_text=kw.pop("question_text", f"Frage {uuid.uuid4().hex[:8]}"),
        question_type="single_choice",
        difficulty="medium",
        topic="Thema",
        review_status=kw.pop("review_status", "pending"),
        visibility=QuestionReviewVisibility.PRIVATE,
        **kw,
    )
    test_db.add(q)
    test_db.flush()
    return q


def _version(test_db, q, number=1, status="pending", **kw):
    v = QuestionVersion(
        question_id=q.id,
        version_number=number,
        question_text=q.question_text,
        question_type=q.question_type,
        difficulty=q.difficulty,
        topic=q.topic,
        review_status=status,
        **kw,
    )
    test_db.add(v)
    test_db.flush()
    return v


def test_version_numbers_are_unique_per_question(test_db):
    q = _question(test_db)
    _version(test_db, q, 1, "approved")
    with pytest.raises(IntegrityError):
        _version(test_db, q, 1, "approved")
    test_db.rollback()


def test_unknown_status_and_edited_are_rejected(test_db):
    q = _question(test_db)
    with pytest.raises(IntegrityError):
        _version(test_db, q, 1, "edited")
    test_db.rollback()


def test_withdrawn_status_is_allowed(test_db):
    q = _question(test_db)
    assert _version(test_db, q, 1, "withdrawn").id is not None


def test_at_most_one_open_version_per_question(test_db):
    q = _question(test_db)
    _version(test_db, q, 1, "approved")
    _version(test_db, q, 2, "pending")
    with pytest.raises(IntegrityError):
        _version(test_db, q, 3, "in_review")
    test_db.rollback()


def test_many_closed_versions_allowed(test_db):
    q = _question(test_db)
    for n, status in enumerate(["approved", "withdrawn", "rejected", "approved"], 1):
        _version(test_db, q, n, status)
    assert [v.version_number for v in q.versions] == [1, 2, 3, 4]


def test_ln_level_range_enforced(test_db):
    q = _question(test_db)
    with pytest.raises(IntegrityError):
        _version(test_db, q, 1, "pending", ln_level=5)
    test_db.rollback()


def test_versions_are_deleted_with_their_question(test_db):
    q = _question(test_db)
    _version(test_db, q, 1, "approved")
    qid = q.id
    test_db.delete(q)
    test_db.flush()
    assert test_db.query(QuestionVersion).filter_by(question_id=qid).count() == 0


@pytest.mark.parametrize("load_versions", [False, True])
def test_orm_delete_question_with_pinned_exam_position(test_db, load_versions):
    exam = _exam(test_db)
    q = _question(test_db)
    v = _version(test_db, q, 1, "approved")
    if load_versions:
        test_db.refresh(q)
        assert len(q.versions) == 1
    test_db.add(
        ExamQuestion(
            exam_id=exam.id,
            question_id=q.id,
            question_version_id=v.id,
            position=1,
            points=1.0,
        )
    )
    test_db.flush()
    qid = q.id
    test_db.delete(q)
    test_db.flush()
    test_db.expire_all()
    assert test_db.query(QuestionVersion).filter_by(question_id=qid).count() == 0
    assert test_db.query(ExamQuestion).filter_by(question_id=qid).count() == 0


def test_pinned_version_cannot_be_deleted_individually(test_db):
    exam = _exam(test_db)
    q = _question(test_db)
    v = _version(test_db, q, 1, "approved")
    test_db.add(
        ExamQuestion(
            exam_id=exam.id,
            question_id=q.id,
            question_version_id=v.id,
            position=1,
            points=1.0,
        )
    )
    test_db.flush()
    with pytest.raises(IntegrityError):
        test_db.execute(
            text("DELETE FROM question_versions WHERE id = :i"), {"i": v.id}
        )
    test_db.rollback()


def test_user_deletion_keeps_version_with_null_author(test_db):
    slug = f"ec192-{uuid.uuid4().hex[:8]}"
    inst = Institution(name=slug, slug=slug, domain=f"{slug}.example.com")
    test_db.add(inst)
    test_db.flush()
    user = User(
        email=f"{slug}@example.com",
        password_hash="x",
        first_name="A",
        last_name="B",
        institution_id=inst.id,
    )
    test_db.add(user)
    test_db.flush()
    q = _question(test_db)
    v = _version(test_db, q, 1, "approved", created_by=user.id, reviewed_by=user.id)
    vid = v.id
    test_db.execute(text("DELETE FROM users WHERE id = :i"), {"i": user.id})
    test_db.expire_all()
    kept = test_db.get(QuestionVersion, vid)
    assert kept is not None and kept.created_by is None and kept.reviewed_by is None


def test_bogus_status_and_number_zero_rejected(test_db):
    q = _question(test_db)
    with pytest.raises(IntegrityError):
        _version(test_db, q, 1, "bogus")
    test_db.rollback()
    q = _question(test_db)
    with pytest.raises(IntegrityError):
        _version(test_db, q, 0, "approved")
    test_db.rollback()


def test_closing_the_open_version_frees_the_slot(test_db):
    q = _question(test_db)
    v1 = _version(test_db, q, 1, "pending")
    v1.review_status = "approved"
    test_db.flush()
    assert _version(test_db, q, 2, "pending").id is not None


def test_check_and_open_index_follow_the_enum():
    from models.question_version import (
        OPEN_VERSION_STATUSES,
        QuestionVersionStatus,
    )

    table = QuestionVersion.__table__
    check = next(
        c for c in table.constraints if c.name == "ck_question_versions_review_status"
    )
    assert all(f"'{s.value}'" in str(check.sqltext) for s in QuestionVersionStatus)
    index = next(i for i in table.indexes if i.name == "uq_question_versions_one_open")
    where = str(index.dialect_options["postgresql"]["where"])
    assert all(f"'{s}'" in where for s in OPEN_VERSION_STATUSES)
    assert set(OPEN_VERSION_STATUSES) < {s.value for s in QuestionVersionStatus}


def _exam(test_db):
    slug = f"ec192-{uuid.uuid4().hex[:8]}"
    inst = Institution(name=slug, slug=slug, domain=f"{slug}.example.com")
    test_db.add(inst)
    test_db.flush()
    exam = Exam(
        title=f"E-{slug}", status="draft", total_points=0, institution_id=inst.id
    )
    test_db.add(exam)
    test_db.flush()
    return exam


def test_exam_question_pins_own_version(test_db):
    exam = _exam(test_db)
    q = _question(test_db)
    v = _version(test_db, q, 1, "approved")
    eq = ExamQuestion(
        exam_id=exam.id,
        question_id=q.id,
        question_version_id=v.id,
        position=1,
        points=1.0,
    )
    test_db.add(eq)
    test_db.flush()
    assert eq.question_version_id == v.id


def test_exam_question_without_pin_still_valid(test_db):
    """Bis EXAMCRAFT-175 schreiben die Pfade den Zeiger noch nicht."""
    exam = _exam(test_db)
    q = _question(test_db)
    eq = ExamQuestion(exam_id=exam.id, question_id=q.id, position=1, points=1.0)
    test_db.add(eq)
    test_db.flush()
    assert eq.question_version_id is None


@pytest.fixture(scope="module")
def migration():
    spec = importlib.util.spec_from_file_location("ec192_question_versions", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_revision_id_fits_limit(migration):
    assert len(migration.revision) <= 32
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[1] / "alembic")
    )
    assert len(ScriptDirectory.from_config(cfg).get_heads()) == 1


def test_migration_backfills_version_one_and_pins_positions(test_db, migration):
    conn = test_db.connection()
    ctx = MigrationContext.configure(conn)
    with Operations.context(ctx):
        # Stand vor der Migration herstellen (alles in der Transaktion).
        migration.downgrade()

    exam_id = _exam(test_db).id
    ids = {}
    for status in ("approved", "edited", "rejected"):
        ids[status] = conn.execute(
            text(
                "INSERT INTO question_reviews (question_text, question_type,"
                " difficulty, topic, review_status, bloom_level, explanation, visibility)"
                " VALUES (:t, 'open_ended', 'easy', 'T', :s, 3, 'Erkl', 'private')"
                " RETURNING id"
            ),
            {"t": f"mig-{status}", "s": status},
        ).scalar()
    conn.execute(
        text(
            "INSERT INTO exam_questions (exam_id, question_id, position, points)"
            " VALUES (:e, :q, 1, 2)"
        ),
        {"e": exam_id, "q": ids["approved"]},
    )

    with Operations.context(MigrationContext.configure(conn)):
        migration.upgrade()

    rows = conn.execute(
        text(
            "SELECT question_id, version_number, review_status, bloom_level,"
            " explanation, question_text FROM question_versions"
            " WHERE question_id = ANY(:ids) ORDER BY question_id"
        ),
        {"ids": list(ids.values())},
    ).all()
    assert len(rows) == 3
    by_q = {r.question_id: r for r in rows}
    assert all(r.version_number == 1 for r in rows)
    assert by_q[ids["approved"]].review_status == "approved"
    assert by_q[ids["edited"]].review_status == "pending"  # edited entfällt
    assert by_q[ids["rejected"]].review_status == "rejected"
    assert by_q[ids["approved"]].bloom_level == 3
    assert by_q[ids["approved"]].explanation == "Erkl"
    assert by_q[ids["approved"]].question_text == "mig-approved"

    pinned = conn.execute(
        text(
            "SELECT eq.question_version_id, qv.id FROM exam_questions eq"
            " JOIN question_versions qv ON qv.question_id = eq.question_id"
            " WHERE eq.exam_id = :e"
        ),
        {"e": exam_id},
    ).one()
    assert pinned.question_version_id == pinned.id

    # Constraints created by the migration itself (not by create_all).
    insert = text(
        "INSERT INTO question_versions (question_id, version_number,"
        " question_text, question_type, difficulty, topic, review_status)"
        " VALUES (:q, 2, 'x', 'open_ended', 'easy', 'T', :s)"
    )
    with pytest.raises(IntegrityError):  # second open version
        with conn.begin_nested():
            conn.execute(insert, {"q": ids["edited"], "s": "in_review"})
    with pytest.raises(IntegrityError):  # edited is no longer a status
        with conn.begin_nested():
            conn.execute(insert, {"q": ids["approved"], "s": "edited"})
    indexdef = conn.execute(
        text(
            "SELECT indexdef FROM pg_indexes"
            " WHERE indexname = 'uq_question_versions_one_open'"
        )
    ).scalar()
    assert "UNIQUE" in indexdef and "WHERE" in indexdef
    test_db.rollback()
