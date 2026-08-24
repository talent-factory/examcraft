"""_persist_questions maps competency_code -> competency_id + ln_level (TF-400)."""

from types import SimpleNamespace

from tasks.question_tasks import _persist_questions
from models.competency import CompetencyFramework, Competency
from models.question_review import QuestionReview


def _setup(test_db):
    from models.auth import Institution, User

    inst = Institution(
        name="Persist Inst",
        slug="persist-inst",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    # QuestionReview.created_by is an FK to users.id — without a real user
    # the INSERT fails on question_reviews_created_by_fkey (independent of
    # the competency logic). We therefore create a user and pass its id
    # through as user_id.
    user = User(
        email="persist@example.com",
        first_name="P",
        last_name="U",
        institution_id=inst.id,
    )
    test_db.add(user)
    test_db.flush()
    fw = CompetencyFramework(
        name="M",
        rendered_text="x",
        institution_id=inst.id,
        visibility="institution",
    )
    test_db.add(fw)
    test_db.flush()
    test_db.add(Competency(framework_id=fw.id, code="B3", title="t", position=1))
    test_db.commit()
    test_db.refresh(fw)
    return inst, fw, user


def _q(**over):
    base = dict(
        question_text="F?",
        question_type="single_choice",
        options={"A": "x"},
        correct_answer="A",
        explanation="e",
        difficulty="medium",
        bloom_level=3,
        source_chunks=[],
        source_documents=[],
        confidence_score=0.9,
        generation_metadata=None,
        estimated_time_minutes=None,
        quality_tier=None,
        competency_code=None,
        ln_level=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_known_code_maps_to_competency_id(test_db):
    inst, fw, user = _setup(test_db)
    _persist_questions(
        [_q(competency_code="B3", ln_level=2)],
        exam_id="tf400-persist-known",
        topic="T",
        language="de",
        user_id=user.id,
        institution_id=inst.id,
        tag_ids=None,
        framework_id=fw.id,
        db=test_db,
    )
    # Scope to this test's own row via its namespaced exam_id. The shared CI
    # test-DB may already hold question_reviews committed by other suites, so a
    # table-wide .one() raises MultipleResultsFound there (TF-400 CI fix).
    row = test_db.query(QuestionReview).filter_by(exam_id="tf400-persist-known").one()
    comp = fw.competencies[0]
    assert row.competency_id == comp.id
    assert row.ln_level == 2


def test_unknown_code_nulls_competency_but_keeps_ln(test_db):
    inst, fw, user = _setup(test_db)
    _persist_questions(
        [_q(competency_code="ZZ9", ln_level=4)],
        exam_id="tf400-persist-unknown",
        topic="T",
        language="de",
        user_id=user.id,
        institution_id=inst.id,
        tag_ids=None,
        framework_id=fw.id,
        db=test_db,
    )
    row = test_db.query(QuestionReview).filter_by(exam_id="tf400-persist-unknown").one()
    assert row.competency_id is None
    assert row.ln_level == 4


def test_out_of_range_ln_level_clamped_to_none(test_db):
    """Model output with an LN level outside 1-4 is reduced to None on
    persist (defensive app-tier guard; the DB CHECK is the backstop)."""
    inst, fw, user = _setup(test_db)
    _persist_questions(
        [_q(competency_code="B3", ln_level=9)],
        exam_id="tf400-persist-ln-oor",
        topic="T",
        language="de",
        user_id=user.id,
        institution_id=inst.id,
        tag_ids=None,
        framework_id=fw.id,
        db=test_db,
    )
    row = test_db.query(QuestionReview).filter_by(exam_id="tf400-persist-ln-oor").one()
    assert row.competency_id == fw.competencies[0].id
    assert row.ln_level is None


def _logged(warn_mock) -> str:
    """All arguments of all logger.warning(...) calls joined into one string."""
    return " ".join(str(a) for call in warn_mock.call_args_list for a in call.args)


def test_unmatched_competency_code_logs_warning(test_db):
    """A non-empty competency_code with no match in the framework map is
    logged — otherwise a total tagging failure (e.g. a mismatched heading
    format) would go unnoticed. The module logger is patched instead of
    using caplog, which catches nothing in the full suite depending on the
    logging configuration."""
    from unittest.mock import patch

    import tasks.question_tasks as qt

    inst, fw, user = _setup(test_db)
    with patch.object(qt.logger, "warning") as warn:
        _persist_questions(
            [_q(competency_code="ZZ9", ln_level=2)],
            exam_id="tf400-persist-warn",
            topic="T",
            language="de",
            user_id=user.id,
            institution_id=inst.id,
            tag_ids=None,
            framework_id=fw.id,
            db=test_db,
        )
    logged = _logged(warn)
    assert "competency_code_unmatched" in logged
    assert "ZZ9" in logged


def test_empty_competency_code_does_not_warn(test_db):
    """An empty/missing code is the legitimate "no tagging desired" case
    and must not produce a competency_code_unmatched warning."""
    from unittest.mock import patch

    import tasks.question_tasks as qt

    inst, fw, user = _setup(test_db)
    with patch.object(qt.logger, "warning") as warn:
        _persist_questions(
            [_q(competency_code=None, ln_level=None)],
            exam_id="tf400-persist-nocode",
            topic="T",
            language="de",
            user_id=user.id,
            institution_id=inst.id,
            tag_ids=None,
            framework_id=fw.id,
            db=test_db,
        )
    assert "competency_code_unmatched" not in _logged(warn)


def test_ln_level_check_constraint_rejects_out_of_range(test_db):
    """DB CHECK check_ln_level_range is the backstop: a direct UPDATE to an
    LN level outside 1-4 must fail (the app already clamps, but the DB must
    not rely on that)."""
    import pytest
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    inst, fw, user = _setup(test_db)
    _persist_questions(
        [_q(competency_code="B3", ln_level=3)],
        exam_id="tf400-ln-check",
        topic="T",
        language="de",
        user_id=user.id,
        institution_id=inst.id,
        tag_ids=None,
        framework_id=fw.id,
        db=test_db,
    )
    with pytest.raises(IntegrityError):
        test_db.execute(
            text(
                "UPDATE question_reviews SET ln_level = 9 "
                "WHERE exam_id = 'tf400-ln-check'"
            )
        )
        test_db.commit()
    test_db.rollback()


def test_no_framework_id_nulls_competency_but_keeps_ln(test_db):
    inst, fw, user = _setup(test_db)
    _persist_questions(
        [_q(competency_code="B3", ln_level=2)],
        exam_id="tf400-persist-noframework",
        topic="T",
        language="de",
        user_id=user.id,
        institution_id=inst.id,
        tag_ids=None,
        framework_id=None,
        db=test_db,
    )
    row = (
        test_db.query(QuestionReview)
        .filter_by(exam_id="tf400-persist-noframework")
        .one()
    )
    assert row.competency_id is None
    assert row.ln_level == 2
