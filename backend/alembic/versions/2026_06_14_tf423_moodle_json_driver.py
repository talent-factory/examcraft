"""tf423: 'moodle_json' in CHECK-Constraints für attempts.source + import_jobs.driver_name

Der JSON-Resultatimport (TF-423) schreibt Attempts/Import-Jobs mit
``source``/``driver_name`` = ``'moodle_json'``. Beide CHECK-Constraints werden
um diesen Wert erweitert. ``'moodle_csv'`` bleibt erlaubt — der CSV-Treiber
wurde entfernt, historische Zeilen tragen den Wert aber weiter und dürfen den
Constraint nicht verletzen.

Additiv und nicht-destruktiv: Die neue Wertemenge ist eine Obermenge der alten,
Altbestand bleibt gültig — unbedenklich unter AUTO_MIGRATE=true.

Revision ID: tf423_moodle_json_driver
Revises: tf410_prompt_visibility
Create Date: 2026-06-14
"""

from typing import Union

from alembic import op

revision: str = "tf423_moodle_json_driver"
down_revision: Union[str, None] = "tf410_prompt_visibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("check_attempt_source", "attempts", type_="check")
    op.create_check_constraint(
        "check_attempt_source",
        "attempts",
        "source IN ('moodle_csv', 'moodle_api', 'moodle_json')",
    )
    op.drop_constraint("check_import_job_driver", "import_jobs", type_="check")
    op.create_check_constraint(
        "check_import_job_driver",
        "import_jobs",
        "driver_name IN ('moodle_csv', 'moodle_api', 'moodle_json')",
    )


def downgrade() -> None:
    op.drop_constraint("check_import_job_driver", "import_jobs", type_="check")
    op.create_check_constraint(
        "check_import_job_driver",
        "import_jobs",
        "driver_name IN ('moodle_csv', 'moodle_api')",
    )
    op.drop_constraint("check_attempt_source", "attempts", type_="check")
    op.create_check_constraint(
        "check_attempt_source",
        "attempts",
        "source IN ('moodle_csv', 'moodle_api')",
    )
