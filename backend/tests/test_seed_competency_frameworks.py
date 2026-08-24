"""Seed test for the BWZ competency framework (TF-400)."""

from models.competency import Competency, CompetencyFramework
from utils.seed_competency_frameworks import seed_bwz_frameworks


def _inst(test_db):
    from models.auth import Institution

    inst = Institution(
        name="Seed BWZ",
        slug="seed-bwz",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.commit()
    test_db.refresh(inst)
    return inst


def test_seed_creates_two_frameworks_idempotently(test_db):
    inst = _inst(test_db)
    seed_bwz_frameworks(test_db, institution_id=inst.id)
    seed_bwz_frameworks(test_db, institution_id=inst.id)  # idempotent

    fws = test_db.query(CompetencyFramework).filter_by(institution_id=inst.id).all()
    names = sorted(f.name for f in fws)
    assert len(fws) == 2
    assert "Mitarbeitende führen" in names[0]  # Module A — correct title
    assert all(f.rendered_text for f in fws)

    # TF-400: structured HKs are derived from rendered_text and are not
    # duplicated after seeding twice (code is unique per framework).
    modul_b = next(f for f in fws if f.module_code == "B")
    codes = sorted(c.code for c in modul_b.competencies)
    assert codes == ["B1", "B2", "B3"]
    total = (
        test_db.query(Competency)
        .filter(Competency.framework_id.in_([f.id for f in fws]))
        .count()
    )
    assert total == 6  # Module A: A1/A2/A6 + Module B: B1/B2/B3
