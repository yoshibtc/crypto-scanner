from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from cgd.db.engine import session_scope
from cgd.db.models import Entity


def get_by_slug(session: Session, slug: str) -> Entity | None:
    return session.scalars(select(Entity).where(Entity.slug == slug)).first()


def list_all(session: Session) -> list[Entity]:
    return list(session.execute(select(Entity)).scalars().all())


def upsert_entity(
    session: Session,
    *,
    slug: str,
    display_name: str,
    llama_protocol_slugs: list[str] | None = None,
    token_addresses: dict[str, Any] | None = None,
    ccxt_symbol_map: dict[str, Any] | None = None,
    rpc_chain: str | None = None,
    supply_source: str = "stub",
    mapping_confidence: float = 0.75,
    enabled_patterns: list[str] | None = None,
    tvl_contract_allowlist: list[str] | None = None,
) -> Entity:
    """Create or update an entity by slug (idempotent)."""
    now = datetime.now(timezone.utc)
    ent = get_by_slug(session, slug)
    if ent is None:
        ent = Entity(
            slug=slug,
            display_name=display_name,
            semantics_version=1,
            llama_protocol_slugs=llama_protocol_slugs or [],
            token_addresses=token_addresses or {},
            ccxt_symbol_map=ccxt_symbol_map or {},
            rpc_chain=rpc_chain,
            supply_source=supply_source,
            mapping_confidence=mapping_confidence,
            enabled_patterns=enabled_patterns or ["P7", "P6", "P10"],
            tvl_contract_allowlist=tvl_contract_allowlist or [],
            created_at=now,
            updated_at=now,
        )
        session.add(ent)
        session.flush()
        return ent

    ent.display_name = display_name
    ent.updated_at = now
    if llama_protocol_slugs is not None:
        ent.llama_protocol_slugs = llama_protocol_slugs
    if token_addresses is not None:
        ent.token_addresses = token_addresses
    if ccxt_symbol_map is not None:
        ent.ccxt_symbol_map = ccxt_symbol_map
    if rpc_chain is not None:
        ent.rpc_chain = rpc_chain
    if supply_source is not None:
        ent.supply_source = supply_source
    if mapping_confidence is not None:
        ent.mapping_confidence = mapping_confidence
    if enabled_patterns is not None:
        ent.enabled_patterns = enabled_patterns
    if tvl_contract_allowlist is not None:
        ent.tvl_contract_allowlist = tvl_contract_allowlist
    return ent


def disable_entity(session: Session, slug: str) -> bool:
    """Disable an entity from evaluation (empty patterns + zero confidence)."""
    ent = get_by_slug(session, slug)
    if ent is None:
        return False
    ent.enabled_patterns = []
    ent.mapping_confidence = 0.0
    ent.updated_at = datetime.now(timezone.utc)
    return True


def list_entities() -> list[Entity]:
    with session_scope() as session:
        return list(session.execute(select(Entity)).scalars().all())
