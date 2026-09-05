"""add_lab_reports_table

Revision ID: 31a8c8e99bdf
Revises: 20bdbf294cbe
Create Date: 2026-09-05 18:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31a8c8e99bdf'
down_revision: Union[str, Sequence[str], None] = '20bdbf294cbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'lab_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('consultation_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, default=0),
        sa.Column('mime_type', sa.String(length=100), nullable=False, default='application/pdf'),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['consultation_id'], ['consultations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_lab_reports_id'), 'lab_reports', ['id'], unique=False)
    op.create_index(op.f('ix_lab_reports_patient_id'), 'lab_reports', ['patient_id'], unique=False)
    op.create_index(op.f('ix_lab_reports_consultation_id'), 'lab_reports', ['consultation_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_lab_reports_consultation_id'), table_name='lab_reports')
    op.drop_index(op.f('ix_lab_reports_patient_id'), table_name='lab_reports')
    op.drop_index(op.f('ix_lab_reports_id'), table_name='lab_reports')
    op.drop_table('lab_reports')
