"""Access lifespan resources without constructing clients for each request."""

from collections.abc import Generator

from fastapi import Request
from qdrant_client import QdrantClient
from sqlalchemy.orm import Session


def get_session(request: Request) -> Generator[Session, None, None]:
    with request.app.state.session_factory() as session:
        yield session


def get_qdrant(request: Request) -> QdrantClient:
    return request.app.state.qdrant_client
