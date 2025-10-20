"""Add GDPR compliance fields to User model

Revision ID: add_gdpr_fields
Revises: 
Create Date: 2025-10-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_gdpr_fields'
down_revision = 'b9585b1a8163'  # increase_avatar_url_length
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add GDPR compliance fields to users table"""
    # Add deletion_requested_at column
    op.add_column('users', sa.Column('deletion_requested_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add scheduled_deletion_date column
    op.add_column('users', sa.Column('scheduled_deletion_date', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove GDPR compliance fields from users table"""
    op.drop_column('users', 'scheduled_deletion_date')
    op.drop_column('users', 'deletion_requested_at')

