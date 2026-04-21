"""add book file type

Revision ID: 20260421_0004
Revises: 20260325_0003
Create Date: 2026-04-21 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260421_0004"
down_revision = "20260325_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("books") as batch_op:
        batch_op.add_column(sa.Column("file_type", sa.String(length=20), nullable=True))

    op.execute("UPDATE books SET file_type = 'epub' WHERE file_type IS NULL")

    with op.batch_alter_table("books") as batch_op:
        batch_op.alter_column("file_type", nullable=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for book file_type migration.")

