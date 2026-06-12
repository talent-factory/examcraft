"""Modell-Tests für Kompetenzrahmen (TF-400)."""

from models.competency import CompetencyFramework, Competency


def _institution(test_db):
    from models.auth import Institution

    inst = Institution(
        name="HKP Test BWZ",
        slug="hkp-test-bwz",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.commit()
    test_db.refresh(inst)
    return inst


def test_create_framework_with_competencies(test_db):
    inst = _institution(test_db)
    fw = CompetencyFramework(
        name="Modul B – Wirkungsvoll kommunizieren",
        module_code="B",
        description="HKB-Beschreibung",
        rendered_text="# HKB ...\n### B1 ...",
        language="de",
        institution_id=inst.id,
        visibility="institution",
    )
    test_db.add(fw)
    test_db.flush()

    c1 = Competency(
        framework_id=fw.id,
        code="B1",
        title="… adressatengerecht kommunizieren",
        descriptors=[{"text": "Sie setzen Kommunikationsmodelle ein.", "ln_level": 2}],
        position=1,
    )
    test_db.add(c1)
    test_db.commit()

    loaded = test_db.query(CompetencyFramework).filter_by(id=fw.id).one()
    assert loaded.module_code == "B"
    assert loaded.visibility == "institution"
    assert loaded.is_archived is False
    assert loaded.competencies[0].code == "B1"
    assert loaded.competencies[0].descriptors[0]["ln_level"] == 2


def test_visibility_check_constraint_rejects_bad_value(test_db):
    import pytest
    from sqlalchemy.exc import IntegrityError

    inst = _institution(test_db)
    fw = CompetencyFramework(
        name="Bad", rendered_text="x", institution_id=inst.id, visibility="public"
    )
    test_db.add(fw)
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_duplicate_competency_code_rejected(test_db):
    import pytest
    from sqlalchemy.exc import IntegrityError

    inst = _institution(test_db)
    fw = CompetencyFramework(
        name="M", rendered_text="x", institution_id=inst.id, visibility="institution"
    )
    test_db.add(fw)
    test_db.flush()
    test_db.add(Competency(framework_id=fw.id, code="B1", title="a", position=1))
    test_db.add(Competency(framework_id=fw.id, code="B1", title="b", position=2))
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()


def test_deleting_framework_cascades_competencies(test_db):
    inst = _institution(test_db)
    fw = CompetencyFramework(
        name="M", rendered_text="x", institution_id=inst.id, visibility="institution"
    )
    test_db.add(fw)
    test_db.flush()
    test_db.add(Competency(framework_id=fw.id, code="A1", title="t", position=1))
    test_db.commit()

    test_db.delete(fw)
    test_db.commit()
    assert test_db.query(Competency).count() == 0


def test_deleting_competency_sets_question_review_competency_id_null(test_db):
    """FK ondelete=SET NULL: löscht man eine Competency, überlebt die
    referenzierende QuestionReview mit competency_id=NULL und unverändertem
    ln_level. Das ist der Vertrag, um den _sync_competencies_from_text bewusst
    nie löscht (sonst gingen Frage-Taggings verloren)."""
    from models.question_review import QuestionReview

    inst = _institution(test_db)
    fw = CompetencyFramework(
        name="M", rendered_text="x", institution_id=inst.id, visibility="institution"
    )
    test_db.add(fw)
    test_db.flush()
    comp = Competency(framework_id=fw.id, code="B3", title="t", position=1)
    test_db.add(comp)
    test_db.flush()
    q = QuestionReview(
        question_text="Frage?",
        question_type="single_choice",
        difficulty="medium",
        topic="Kommunikation",
        competency_id=comp.id,
        ln_level=3,
    )
    test_db.add(q)
    test_db.commit()
    qid = q.id

    test_db.delete(comp)
    test_db.commit()
    test_db.expire_all()

    survived = test_db.query(QuestionReview).filter_by(id=qid).one()
    assert survived.competency_id is None  # SET NULL, Frage überlebt
    assert survived.ln_level == 3  # unverändert


def test_db_level_cascade_deletes_competencies_on_framework_delete(test_db):
    """ON DELETE CASCADE auf competencies.framework_id greift auch bei einem
    DELETE, das die ORM-Beziehung umgeht (z. B. Bulk-Delete) — die
    Relationship-Cascade allein würde das nicht abdecken."""
    from sqlalchemy import text

    inst = _institution(test_db)
    fw = CompetencyFramework(
        name="M", rendered_text="x", institution_id=inst.id, visibility="institution"
    )
    test_db.add(fw)
    test_db.flush()
    test_db.add(Competency(framework_id=fw.id, code="A1", title="t", position=1))
    test_db.commit()
    fid = fw.id

    test_db.execute(text("DELETE FROM competency_frameworks WHERE id = :i"), {"i": fid})
    test_db.commit()
    assert test_db.query(Competency).filter_by(framework_id=fid).count() == 0


def test_question_review_links_competency(test_db):
    from models.question_review import QuestionReview

    inst = _institution(test_db)
    fw = CompetencyFramework(
        name="M", rendered_text="x", institution_id=inst.id, visibility="institution"
    )
    test_db.add(fw)
    test_db.flush()
    comp = Competency(framework_id=fw.id, code="B3", title="t", position=1)
    test_db.add(comp)
    test_db.flush()

    q = QuestionReview(
        question_text="Frage?",
        question_type="single_choice",
        difficulty="medium",
        topic="Kommunikation",
        competency_id=comp.id,
        ln_level=3,
    )
    test_db.add(q)
    test_db.commit()

    loaded = test_db.query(QuestionReview).filter_by(id=q.id).one()
    assert loaded.competency_id == comp.id
    assert loaded.ln_level == 3
    assert loaded.bloom_level is None  # distinkt
