"""initial schema with timescale market_facts

Revision ID: 001
Revises:
Create Date: 2026-04-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))

    op.create_table(
        "entities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("semantics_version", sa.Integer(), nullable=False),
        sa.Column("llama_protocol_slugs", sa.JSON(), nullable=False),
        sa.Column("token_addresses", sa.JSON(), nullable=False),
        sa.Column("ccxt_symbol_map", sa.JSON(), nullable=False),
        sa.Column("rpc_chain", sa.String(length=64), nullable=True),
        sa.Column("supply_source", sa.String(length=64), nullable=False),
        sa.Column("mapping_confidence", sa.Float(), nullable=False),
        sa.Column("enabled_patterns", sa.JSON(), nullable=False),
        sa.Column("tvl_contract_allowlist", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "market_facts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("fact_type", sa.String(length=64), nullable=False),
        sa.Column("venue_id", sa.String(length=64), nullable=True),
        sa.Column("pool_id", sa.String(length=256), nullable=True),
        sa.Column("source_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id", "source_ts"),
    )
    op.create_index(
        "ix_market_facts_entity_type_ts",
        "market_facts",
        ["entity_id", "fact_type", "source_ts"],
    )
    op.execute(
        sa.text(
            "SELECT create_hypertable('market_facts', 'source_ts', "
            "chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);"
        )
    )

    op.create_table(
        "onchain_facts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("fact_type", sa.String(length=64), nullable=False),
        sa.Column("chain", sa.String(length=64), nullable=False),
        sa.Column("contract_address", sa.String(length=128), nullable=True),
        sa.Column("source_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_onchain_facts_entity_type_ts",
        "onchain_facts",
        ["entity_id", "fact_type", "source_ts"],
    )

    op.create_table(
        "gaps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pattern_id", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("dedupe_key", sa.String(length=512), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("supporting_observation_refs", sa.JSON(), nullable=False),
        sa.Column("alert_dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pattern_id", "dedupe_key", name="uq_gaps_pattern_dedupe"),
    )
    op.create_index("ix_gaps_entity_status", "gaps", ["entity_id", "status"])

    op.create_table(
        "gap_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gap_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["gap_id"], ["gaps.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "source_health",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_key", sa.String(length=128), nullable=False),
        sa.Column("venue_id", sa.String(length=64), nullable=True),
        sa.Column("success_streak", sa.Integer(), nullable=False),
        sa.Column("fail_streak", sa.Integer(), nullable=False),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_ok_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key", "venue_id", name="uq_source_health_key_venue"),
    )

    op.create_table(
        "ingestion_cursors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_key", sa.String(length=128), nullable=False),
        sa.Column("cursor_value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("semantics_version", sa.Integer(), nullable=False),
        sa.Column("matrix_version", sa.Integer(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inputs_hash", sa.String(length=128), nullable=False),
        sa.Column("shadow_mode", sa.Boolean(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "gap_outcomes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gap_id", sa.Integer(), nullable=False),
        sa.Column("actionable", sa.Boolean(), nullable=True),
        sa.Column("still_true_7d", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("labeled_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["gap_id"], ["gaps.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("gap_outcomes")
    op.drop_table("evaluation_runs")
    op.drop_table("ingestion_cursors")
    op.drop_table("source_health")
    op.drop_table("gap_events")
    op.drop_table("gaps")
    op.drop_table("onchain_facts")
    op.execute(sa.text("DROP TABLE IF EXISTS market_facts CASCADE"))
    op.drop_table("entities")
