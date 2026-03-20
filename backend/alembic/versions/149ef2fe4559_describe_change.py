"""describe change

Revision ID: 149ef2fe4559
Revises: 20260320_0001
Create Date: 2026-03-20 12:55:27.795386
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '149ef2fe4559'
down_revision = '20260320_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_jobs") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=True)

    with op.batch_alter_table("analysis_results") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=True)

    with op.batch_alter_table("user_vocabularies") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=True)

    with op.batch_alter_table("user_vocabulary_items") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("user_vocabulary_items") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=False)

    with op.batch_alter_table("user_vocabularies") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=False)

    with op.batch_alter_table("analysis_results") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=False)

    with op.batch_alter_table("analysis_jobs") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=False)
