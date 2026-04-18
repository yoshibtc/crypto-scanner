"""gap resolve_miss_streak; drop unused ingestion_cursors

Revision ID: 002
Revises: 001
Create Date: 2026-04-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "gaps",
        sa.Column("resolve_miss_streak", sa.Integer(), nullable=False, server_default="0"),
    )
    op.drop_table("ingestion_cursors")


def downgrade() -> None:
    op.create_table(
        "ingestion_cursors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_key", sa.String(length=128), nullable=False),
        sa.Column("cursor_value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    op.drop_column("gaps", "resolve_miss_streak")
