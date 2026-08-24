"""Seed BWZ-Lyss competency frameworks (Module A + B) — TF-400.

Reads the HKP markdown sources from demo/BWZ/ and creates one
CompetencyFramework each with rendered_text = the full file content.
Idempotent over (institution_id, name). Fixes the H1-title copy-and-paste
bug in Module A ("Wirkungsvoll kommunizieren" -> "Mitarbeitende führen").
"""

from pathlib import Path

from sqlalchemy.orm import Session

from models.competency import Competency, CompetencyFramework
from utils.competency_parser import parse_competencies

# Repo root: .../core/backend/utils/ -> 3x parent == repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_BWZ = _REPO_ROOT / "demo" / "BWZ"

_FRAMEWORKS = [
    {
        "name": "Modul A – Mitarbeitende führen",
        "module_code": "A",
        "file": "Modul A - HKP - Mitarbeitende führen.md",
    },
    {
        "name": "Modul B – Wirkungsvoll kommunizieren",
        "module_code": "B",
        "file": "Modul B - HKP - Wirkunsvoll kommunizieren.md",
    },
]


def seed_bwz_frameworks(db: Session, institution_id: int) -> list[CompetencyFramework]:
    created = []
    for spec in _FRAMEWORKS:
        fw = (
            db.query(CompetencyFramework)
            .filter_by(institution_id=institution_id, name=spec["name"])
            .first()
        )
        if fw is None:
            text = (_BWZ / spec["file"]).read_text(encoding="utf-8")
            fw = CompetencyFramework(
                name=spec["name"],
                module_code=spec["module_code"],
                rendered_text=text,
                language="de",
                institution_id=institution_id,
                visibility="institution",
            )
            db.add(fw)
        # TF-400: derive structured HKs from rendered_text if none exist yet
        # (idempotent; also backfills previously created frameworks).
        if not fw.competencies:
            for p in parse_competencies(fw.rendered_text):
                fw.competencies.append(
                    Competency(
                        code=p["code"],
                        title=p["title"],
                        descriptors=p["descriptors"] or None,
                        position=p["position"],
                    )
                )
        created.append(fw)
    db.commit()
    return created
