"""Add created_by column to question_reviews table

Revision ID: 012
Revises: 011_fix_question_reviews_reviewed_by_type
Create Date: 2025-10-21 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add created_by column to question_reviews table
    op.add_column('question_reviews', sa.Column('created_by', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_question_reviews_created_by',
        'question_reviews',
        'users',
        ['created_by'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign key
    op.drop_constraint('fk_question_reviews_created_by', 'question_reviews', type_='foreignkey')
    
    # Drop column
    op.drop_column('question_reviews', 'created_by')

