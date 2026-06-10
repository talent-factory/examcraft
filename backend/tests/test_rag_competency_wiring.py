"""Tests für die Kompetenz-Auflösung im Generierungs-Request (TF-400)."""

from api.rag_exams import resolve_competencies_text


def _fw(test_db, rendered="# HKB B\n### B1 ..."):
    from models.auth import Institution
    from models.competency import CompetencyFramework

    inst = Institution(
        name="Wire Inst",
        slug="wire-inst",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    fw = CompetencyFramework(
        name="Modul B",
        module_code="B",
        rendered_text=rendered,
        institution_id=inst.id,
        visibility="institution",
    )
    test_db.add(fw)
    test_db.commit()
    test_db.refresh(fw)
    return fw, inst


def test_override_wins_over_framework(test_db):
    fw, inst = _fw(test_db)
    out = resolve_competencies_text(
        test_db,
        framework_id=fw.id,
        override="NUR DIES",
        institution_id=inst.id,
    )
    assert out == "NUR DIES"


def test_framework_rendered_text_used(test_db):
    fw, inst = _fw(test_db, rendered="VOLLTEXT HKB")
    out = resolve_competencies_text(
        test_db,
        framework_id=fw.id,
        override=None,
        institution_id=inst.id,
    )
    assert out == "VOLLTEXT HKB"


def test_none_when_no_framework_and_no_override(test_db):
    out = resolve_competencies_text(
        test_db,
        framework_id=None,
        override=None,
        institution_id=1,
    )
    assert out is None


def test_framework_other_institution_not_leaked(test_db):
    fw, inst = _fw(test_db)
    out = resolve_competencies_text(
        test_db,
        framework_id=fw.id,
        override=None,
        institution_id=inst.id + 999,
    )
    assert out is None  # cross-institution → not found → None


def test_archived_framework_not_resolved(test_db):
    """Ein archiviertes Framework wird nicht mehr in den Prompt injiziert."""
    fw, inst = _fw(test_db, rendered="ARCHIVIERT")
    fw.is_archived = True
    test_db.commit()
    out = resolve_competencies_text(
        test_db, framework_id=fw.id, override=None, institution_id=inst.id
    )
    assert out is None


def test_requested_but_missing_framework_logs_warning(test_db):
    """Ein explizit gewähltes, aber nicht auflösbares framework_id (fremde
    Institution / archiviert / gelöscht) wird geloggt — sonst bliebe das stille
    Ausbleiben der Kompetenz-Injektion unauffindbar. Modul-Logger gepatcht statt
    caplog (das in der Gesamt-Suite je nach Logging-Konfig nichts fängt)."""
    from unittest.mock import patch

    import api.rag_exams as rag_exams_mod

    fw, inst = _fw(test_db)
    with patch.object(rag_exams_mod.logger, "warning") as warn:
        out = resolve_competencies_text(
            test_db,
            framework_id=fw.id,
            override=None,
            institution_id=inst.id + 999,  # fremde Institution
        )
    assert out is None
    logged = " ".join(str(a) for call in warn.call_args_list for a in call.args)
    assert "resolve_competencies_text" in logged
    assert str(fw.id) in logged
