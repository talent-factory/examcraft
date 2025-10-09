"""Add chat tables for document chatbot

Revision ID: 004
Revises: None
Create Date: 2025-10-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '004'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create chat_sessions and chat_messages tables"""
    
    # Chat Sessions Table
    op.create_table(
        'chat_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(100), nullable=True),  # Temporär als String, bis User-Management implementiert ist
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('document_ids', sa.ARRAY(sa.Integer), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('message_count', sa.Integer, default=0, nullable=False),
        sa.Column('is_exported_as_document', sa.Boolean, default=False, nullable=False),
        sa.Column('exported_document_id', sa.Integer, nullable=True),  # No FK constraint - will be added later if needed
    )
    
    # Chat Messages Table
    op.create_table(
        'chat_messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),  # 'user' or 'assistant'
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('sources', JSONB, nullable=True),  # Quellenreferenzen aus RAG
        sa.Column('timestamp', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('confidence', sa.Float, nullable=True),  # Confidence score from AI
    )
    
    # Indexes für Performance
    op.create_index('idx_chat_sessions_user_id', 'chat_sessions', ['user_id'])
    op.create_index('idx_chat_sessions_created_at', 'chat_sessions', ['created_at'])
    op.create_index('idx_chat_sessions_updated_at', 'chat_sessions', ['updated_at'])
    op.create_index('idx_chat_messages_session_id', 'chat_messages', ['session_id'])
    op.create_index('idx_chat_messages_timestamp', 'chat_messages', ['timestamp'])
    op.create_index('idx_chat_messages_role', 'chat_messages', ['role'])


def downgrade():
    """Drop chat tables"""
    op.drop_index('idx_chat_messages_role', table_name='chat_messages')
    op.drop_index('idx_chat_messages_timestamp', table_name='chat_messages')
    op.drop_index('idx_chat_messages_session_id', table_name='chat_messages')
    op.drop_index('idx_chat_sessions_updated_at', table_name='chat_sessions')
    op.drop_index('idx_chat_sessions_created_at', table_name='chat_sessions')
    op.drop_index('idx_chat_sessions_user_id', table_name='chat_sessions')
    
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')

