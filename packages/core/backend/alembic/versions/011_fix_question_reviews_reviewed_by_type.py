"""Fix question_reviews.reviewed_by column type from VARCHAR to INTEGER

Revision ID: 011
Revises: 010_add_institution_id_to_question_reviews
Create Date: 2025-10-21 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, set non-numeric reviewed_by values to NULL
    op.execute("""
        UPDATE question_reviews 
        SET reviewed_by = NULL 
        WHERE reviewed_by IS NOT NULL AND reviewed_by !~ '^[0-9]+$'
    """)
    
    # Alter the column type from VARCHAR to INTEGER
    op.execute("""
        ALTER TABLE question_reviews 
        ALTER COLUMN reviewed_by TYPE INTEGER USING reviewed_by::integer
    """)
    
    # Add the foreign key constraint
    op.create_foreign_key(
        'fk_question_reviews_reviewed_by',
        'question_reviews',
        'users',
        ['reviewed_by'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop the foreign key constraint
    op.drop_constraint('fk_question_reviews_reviewed_by', 'question_reviews', type_='foreignkey')
    
    # Alter the column type back to VARCHAR
    op.execute("""
        ALTER TABLE question_reviews 
        ALTER COLUMN reviewed_by TYPE VARCHAR(100)
    """)

