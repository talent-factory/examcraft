"""Add institution_id column to documents table

Revision ID: 008
Revises: 007_add_dynamic_rbac_system
Create Date: 2025-10-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007_add_dynamic_rbac_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add institution_id column to documents table
    op.add_column('documents', sa.Column('institution_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_documents_institution_id',
        'documents',
        'institutions',
        ['institution_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Add index for better query performance
    op.create_index('ix_documents_institution_id', 'documents', ['institution_id'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_documents_institution_id', table_name='documents')
    
    # Drop foreign key
    op.drop_constraint('fk_documents_institution_id', 'documents', type_='foreignkey')
    
    # Drop column
    op.drop_column('documents', 'institution_id')

