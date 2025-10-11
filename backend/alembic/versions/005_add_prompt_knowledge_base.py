"""Add Prompt Knowledge Base tables

Revision ID: 005
Revises: 004
Create Date: 2025-01-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Create prompts, prompt_templates, and prompt_usage_logs tables"""
    
    # Create prompts table
    op.create_table(
        'prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.Text()), server_default='{}'),
        sa.Column('use_case', sa.String(255)),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True)),
        sa.Column('author_id', sa.String(255)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime()),
        sa.Column('usage_count', sa.Integer(), server_default='0'),
        sa.Column('tokens_estimated', sa.Integer()),
        sa.Column('qdrant_point_id', sa.String(255)),
        sa.ForeignKeyConstraint(['parent_id'], ['prompts.id']),
        sa.CheckConstraint(
            "category IN ('system_prompt', 'user_prompt', 'few_shot_example', 'template')",
            name='check_category'
        ),
        sa.CheckConstraint('version > 0', name='check_version')
    )
    
    # Create indexes for prompts table
    op.create_index('idx_prompts_name', 'prompts', ['name'])
    op.create_index('idx_prompts_category', 'prompts', ['category'])
    op.create_index('idx_prompts_is_active', 'prompts', ['is_active'])
    op.create_index('idx_prompts_use_case', 'prompts', ['use_case'])
    op.create_index('idx_prompts_tags', 'prompts', ['tags'], postgresql_using='gin')
    op.create_index('idx_prompts_updated_at', 'prompts', [sa.text('updated_at DESC')])
    
    # Create prompt_templates table
    op.create_table(
        'prompt_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('template', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSONB(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.CheckConstraint(
            "category IN ('question_generation', 'chatbot', 'evaluation')",
            name='check_template_category'
        )
    )
    
    # Create indexes for prompt_templates table
    op.create_index('idx_prompt_templates_name', 'prompt_templates', ['name'])
    op.create_index('idx_prompt_templates_category', 'prompt_templates', ['category'])
    
    # Create prompt_usage_logs table
    op.create_table(
        'prompt_usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True)),
        sa.Column('prompt_version', sa.Integer()),
        sa.Column('use_case', sa.String(255)),
        sa.Column('context_data', postgresql.JSONB()),
        sa.Column('tokens_used', sa.Integer()),
        sa.Column('latency_ms', sa.Integer()),
        sa.Column('success', sa.Boolean(), server_default='true'),
        sa.Column('error_message', sa.Text()),
        sa.Column('user_id', sa.String(255)),
        sa.Column('session_id', sa.String(255)),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ondelete='SET NULL')
    )
    
    # Create indexes for prompt_usage_logs table
    op.create_index('idx_prompt_usage_logs_prompt_id', 'prompt_usage_logs', ['prompt_id'])
    op.create_index('idx_prompt_usage_logs_timestamp', 'prompt_usage_logs', [sa.text('timestamp DESC')])
    op.create_index('idx_prompt_usage_logs_use_case', 'prompt_usage_logs', ['use_case'])


def downgrade():
    """Drop all Prompt Knowledge Base tables"""
    op.drop_table('prompt_usage_logs')
    op.drop_table('prompt_templates')
    op.drop_table('prompts')

