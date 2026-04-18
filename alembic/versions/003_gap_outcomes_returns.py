"""gap_outcomes forward-return columns

Revision ID: 003
Revises: 002
Create Date: 2026-04-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("gap_outcomes", sa.Column("ret_1h_pct", sa.Float(), nullable=True))
    op.add_column("gap_outcomes", sa.Column("ret_4h_pct", sa.Float(), nullable=True))
    op.add_column("gap_outcomes", sa.Column("ret_24h_pct", sa.Float(), nullable=True))
    op.add_column("gap_outcomes", sa.Column("ret_7d_pct", sa.Float(), nullable=True))
    op.add_column(
        "gap_outcomes",
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("gap_outcomes", "computed_at")
    op.drop_column("gap_outcomes", "ret_7d_pct")
    op.drop_column("gap_outcomes", "ret_24h_pct")
    op.drop_column("gap_outcomes", "ret_4h_pct")
    op.drop_column("gap_outcomes", "ret_1h_pct")
