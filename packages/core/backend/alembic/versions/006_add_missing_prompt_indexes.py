"""Add missing indexes for prompts table

Revision ID: 006
Revises: 005
Create Date: 2025-01-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing GIN index for tags and DESC index for updated_at"""
    
    # Check if indexes already exist before creating
    # This handles the case where they were manually created
    
    # GIN index for tags array search
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_prompts_tags'
            ) THEN
                CREATE INDEX idx_prompts_tags ON prompts USING GIN(tags);
            END IF;
        END
        $$;
    """)
    
    # DESC index for updated_at sorting
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'idx_prompts_updated_at'
            ) THEN
                CREATE INDEX idx_prompts_updated_at ON prompts(updated_at DESC);
            END IF;
        END
        $$;
    """)


def downgrade():
    """Remove the indexes"""
    op.drop_index('idx_prompts_updated_at', table_name='prompts')
    op.drop_index('idx_prompts_tags', table_name='prompts')

