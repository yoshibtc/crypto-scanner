from __future__ import annotations

from sqlalchemy import select

from cgd.db.engine import session_scope
from cgd.db.models import Entity


def list_entities() -> list[Entity]:
    with session_scope() as session:
        return list(session.execute(select(Entity)).scalars().all())
