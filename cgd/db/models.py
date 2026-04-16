from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class GapStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    INVALIDATED = "INVALIDATED"


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    semantics_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    llama_protocol_slugs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    token_addresses: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    ccxt_symbol_map: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rpc_chain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supply_source: Mapped[str] = mapped_column(String(64), nullable=False, default="coingecko_stub")
    mapping_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    enabled_patterns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tvl_contract_allowlist: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    gaps: Mapped[list[Gap]] = relationship(back_populates="entity")


class MarketFact(Base):
    __tablename__ = "market_facts"

    id: Mapped[int] = mapped_column(BigInteger, autoincrement=True, nullable=False)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    fact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    venue_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pool_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        PrimaryKeyConstraint("id", "source_ts"),
        Index("ix_market_facts_entity_type_ts", "entity_id", "fact_type", "source_ts"),
    )


class OnchainFact(Base):
    __tablename__ = "onchain_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    fact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    chain: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (Index("ix_onchain_facts_entity_type_ts", "entity_id", "fact_type", "source_ts"),)


class Gap(Base):
    __tablename__ = "gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pattern_id: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=GapStatus.DETECTED.value)
    dedupe_key: Mapped[str] = mapped_column(String(512), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    supporting_observation_refs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    alert_dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    entity: Mapped[Entity] = relationship(back_populates="gaps")
    events: Mapped[list[GapEvent]] = relationship(back_populates="gap", order_by="GapEvent.id")

    __table_args__ = (
        UniqueConstraint("pattern_id", "dedupe_key", name="uq_gaps_pattern_dedupe"),
        Index("ix_gaps_entity_status", "entity_id", "status"),
    )


class GapEvent(Base):
    __tablename__ = "gap_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gap_id: Mapped[int] = mapped_column(ForeignKey("gaps.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    gap: Mapped[Gap] = relationship(back_populates="events")


class SourceHealth(Base):
    __tablename__ = "source_health"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_key: Mapped[str] = mapped_column(String(128), nullable=False)
    venue_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    success_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("source_key", "venue_id", name="uq_source_health_key_venue"),
    )


class IngestionCursor(Base):
    __tablename__ = "ingestion_cursors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    cursor_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    semantics_version: Mapped[int] = mapped_column(Integer, nullable=False)
    matrix_version: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    inputs_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    shadow_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GapOutcome(Base):
    __tablename__ = "gap_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gap_id: Mapped[int] = mapped_column(ForeignKey("gaps.id"), nullable=False)
    actionable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    still_true_7d: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    labeled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
