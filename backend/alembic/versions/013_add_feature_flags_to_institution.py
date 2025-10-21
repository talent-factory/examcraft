"""Add feature flags and update quotas for institutions

Revision ID: 013
Revises: 012
Create Date: 2025-10-21 19:00:00.000000

Fügt features_enabled Array-Spalte hinzu und aktualisiert Quotas
gemäß TF-116 Monetarisierungsstrategie (Free Tier: 5 docs, 20 questions/month, 1 user)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add features_enabled column (ARRAY of strings for manual feature overrides)
    op.add_column(
        'institutions',
        sa.Column('features_enabled', postgresql.ARRAY(sa.String()), nullable=True)
    )

    # Update default quotas to match Free Tier (TF-116)
    op.alter_column(
        'institutions',
        'max_documents',
        server_default='5',
        existing_type=sa.Integer(),
        existing_nullable=False
    )

    op.alter_column(
        'institutions',
        'max_questions_per_month',
        server_default='20',
        existing_type=sa.Integer(),
        existing_nullable=False
    )

    op.alter_column(
        'institutions',
        'max_users',
        server_default='1',
        existing_type=sa.Integer(),
        existing_nullable=False
    )

    # Update existing institutions to Free Tier defaults (if they have old values)
    op.execute("""
        UPDATE institutions
        SET
            max_documents = CASE
                WHEN max_documents = 100 THEN 5
                ELSE max_documents
            END,
            max_questions_per_month = CASE
                WHEN max_questions_per_month = 500 THEN 20
                ELSE max_questions_per_month
            END,
            max_users = CASE
                WHEN max_users = 5 THEN 1
                ELSE max_users
            END
        WHERE subscription_tier = 'free';
    """)


def downgrade() -> None:
    # Revert quota defaults to old values
    op.alter_column(
        'institutions',
        'max_users',
        server_default='5',
        existing_type=sa.Integer(),
        existing_nullable=False
    )

    op.alter_column(
        'institutions',
        'max_questions_per_month',
        server_default='500',
        existing_type=sa.Integer(),
        existing_nullable=False
    )

    op.alter_column(
        'institutions',
        'max_documents',
        server_default='100',
        existing_type=sa.Integer(),
        existing_nullable=False
    )

    # Drop features_enabled column
    op.drop_column('institutions', 'features_enabled')
