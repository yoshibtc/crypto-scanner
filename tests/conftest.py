"""Pytest fixtures shared across CGD tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine


@pytest.fixture
def memory_engine(monkeypatch):
    """Single sqlite :memory: DB shared with `cgd.db.engine.get_engine`."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    from cgd.settings import get_settings

    get_settings.cache_clear()

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    import cgd.db.engine as db_eng

    monkeypatch.setattr(db_eng, "get_engine", lambda: engine)
    db_eng.SessionLocal = None

    from cgd.db.models import Base, Entity, EvaluationRun, Gap, GapEvent

    # SQLite cannot compile market_facts (composite PK + autoincrement); create only test tables.
    Base.metadata.create_all(
        engine,
        tables=[
            Entity.__table__,
            Gap.__table__,
            GapEvent.__table__,
            EvaluationRun.__table__,
        ],
    )
    yield engine
    Base.metadata.drop_all(
        engine,
        tables=[
            EvaluationRun.__table__,
            GapEvent.__table__,
            Gap.__table__,
            Entity.__table__,
        ],
    )
    db_eng.SessionLocal = None
    get_settings.cache_clear()
