"""Add institution_id column to question_reviews table

Revision ID: 010
Revises: 009_fix_documents_user_id_type
Create Date: 2025-10-21 10:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add institution_id column to question_reviews table
    op.add_column('question_reviews', sa.Column('institution_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_question_reviews_institution_id',
        'question_reviews',
        'institutions',
        ['institution_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Add index for better query performance
    op.create_index('ix_question_reviews_institution_id', 'question_reviews', ['institution_id'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_question_reviews_institution_id', table_name='question_reviews')
    
    # Drop foreign key
    op.drop_constraint('fk_question_reviews_institution_id', 'question_reviews', type_='foreignkey')
    
    # Drop column
    op.drop_column('question_reviews', 'institution_id')

