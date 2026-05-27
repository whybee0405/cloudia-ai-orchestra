"""
Database session management for the CloudIA backend.

Provides:
  - `get_session`  — FastAPI dependency (generator) for request-scoped sessions.
  - `get_db`       — Context manager for use in agents, Celery tasks, and scripts.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.db.models import Base  # noqa: F401 — imported so Base.metadata is populated

_is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(
    settings.database_url,
    pool_pre_ping=not _is_sqlite,
    **({} if _is_sqlite else {"pool_size": 5, "max_overflow": 10, "pool_timeout": 30}),
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy Session.

    Usage in a route:

        from fastapi import Depends
        from sqlalchemy.orm import Session
        from backend.db.session import get_session

        @router.get("/example")
        def example(db: Session = Depends(get_session)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager that provides a transactional database session.

    Commits on clean exit, rolls back on exception, always closes the session.

    Usage in agents / Celery tasks:

        from backend.db.session import get_db

        with get_db() as db:
            project = db.query(Project).get(project_id)
            project.status = ProjectStatus.BUILDING
            # committed automatically on exit
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
