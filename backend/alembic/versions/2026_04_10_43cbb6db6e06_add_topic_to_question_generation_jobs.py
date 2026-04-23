"""add_topic_to_question_generation_jobs

Revision ID: 43cbb6db6e06
Revises: 06668c037bdb
Create Date: 2026-04-10 11:12:34.811682

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "43cbb6db6e06"
down_revision: Union[str, None] = "06668c037bdb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: topic/question_count/status were already added by 949c9f5b8da2
    # (2026-03-19). This revision diverged on a branch created before
    # 949c9f5b8da2 existed and would duplicate those columns.
    pass


def downgrade() -> None:
    pass
