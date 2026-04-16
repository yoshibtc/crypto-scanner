from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from cgd.db.models import Entity


def get_by_slug(session: Session, slug: str) -> Entity | None:
    return session.execute(select(Entity).where(Entity.slug == slug)).scalar_one_or_none()


def list_all(session: Session) -> list[Entity]:
    return list(session.execute(select(Entity)).scalars().all())
