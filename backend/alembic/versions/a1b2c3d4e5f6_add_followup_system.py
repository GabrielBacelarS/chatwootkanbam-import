"""add_followup_system

Revision ID: a1b2c3d4e5f6
Revises: 3fe0513251df
Create Date: 2026-02-23 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'fb043f3a9b0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionar campos de follow-up na tabela ai_config
    op.add_column('ai_config', sa.Column('followup_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('ai_config', sa.Column('followup_max_count', sa.Integer(), nullable=True, server_default='3'))
    op.add_column('ai_config', sa.Column('followup_delay_hours', sa.Integer(), nullable=True, server_default='24'))
    op.add_column('ai_config', sa.Column('followup_delay_minutes', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('ai_config', sa.Column('followup_message_template', sa.Text(), nullable=True))

    # Criar tabela followup_jobs
    op.create_table('followup_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_slug', sa.String(length=100), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('followup_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_reason', sa.String(length=200), nullable=True),
        sa.Column('message_sent', sa.String(length=2000), nullable=True),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['client_slug'], ['clients.slug'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Criar indices
    op.create_index(op.f('ix_followup_jobs_id'), 'followup_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_followup_jobs_conversation_id'), 'followup_jobs', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_followup_jobs_scheduled_at'), 'followup_jobs', ['scheduled_at'], unique=False)
    op.create_index('ix_followup_jobs_pending', 'followup_jobs', ['status', 'scheduled_at'], unique=False)
    op.create_index('ix_followup_jobs_conversation', 'followup_jobs', ['client_slug', 'conversation_id', 'status'], unique=False)


def downgrade() -> None:
    # Remover indices
    op.drop_index('ix_followup_jobs_conversation', table_name='followup_jobs')
    op.drop_index('ix_followup_jobs_pending', table_name='followup_jobs')
    op.drop_index(op.f('ix_followup_jobs_scheduled_at'), table_name='followup_jobs')
    op.drop_index(op.f('ix_followup_jobs_conversation_id'), table_name='followup_jobs')
    op.drop_index(op.f('ix_followup_jobs_id'), table_name='followup_jobs')

    # Remover tabela
    op.drop_table('followup_jobs')

    # Remover colunas de ai_config
    op.drop_column('ai_config', 'followup_message_template')
    op.drop_column('ai_config', 'followup_delay_minutes')
    op.drop_column('ai_config', 'followup_delay_hours')
    op.drop_column('ai_config', 'followup_max_count')
    op.drop_column('ai_config', 'followup_enabled')
