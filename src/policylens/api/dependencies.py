"""Access lifespan resources without constructing clients for each request."""

from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from policylens.api.auth import AuthError, token_user_id

_bearer = HTTPBearer(auto_error=False)


def get_session(request: Request) -> Generator[Session, None, None]:
    with request.app.state.session_factory() as session:
        yield session


def get_qdrant(request: Request) -> QdrantClient:
    return request.app.state.qdrant_client


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> UUID:
    """Resolve identity from a verified access token, never from request-body fields."""
    if credentials is None:
        raise AuthError(401, "authentication_required", "A bearer access token is required.")
    return token_user_id(session, credentials.credentials, "access")
