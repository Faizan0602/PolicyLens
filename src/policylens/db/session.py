"""Database session and engine management for PolicyLens."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from policylens.config import get_settings


class Base(DeclarativeBase):
    """Base declarative class for all PolicyLens database models."""

    pass


def get_engine(url: str | None = None, **engine_options):
    """Create an engine from configuration, with optional SQLAlchemy connection options."""
    settings = get_settings()
    db_url = url or settings.database_url
    return create_engine(db_url, **engine_options)


def get_session_factory(engine=None) -> sessionmaker[Session]:
    """Return a sessionmaker factory bound to the provided or default engine."""
    eng = engine or get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=eng)


def get_db(url: str | None = None) -> Generator[Session, None, None]:
    """Context generator yielding a transactional database session."""
    engine = get_engine(url)
    session_factory = get_session_factory(engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
