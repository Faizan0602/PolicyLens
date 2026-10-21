"""Access lifespan resources without constructing clients for each request."""

from collections.abc import Generator
from ipaddress import ip_address

from fastapi import HTTPException, Request
from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from policylens.config import get_settings


def get_session(request: Request) -> Generator[Session, None, None]:
    with request.app.state.session_factory() as session:
        yield session


def get_qdrant(request: Request) -> QdrantClient:
    return request.app.state.qdrant_client


def require_local_demo(request: Request) -> None:
    """Fail closed unless explicitly enabled and accessed directly over loopback."""
    settings = get_settings()
    if not settings.demo_chat_enabled or settings.environment != "development":
        raise HTTPException(
            status_code=403,
            detail={"code": "demo_chat_disabled", "message": "Local development chat is disabled."},
        )
    try:
        local_peer = request.client is not None and ip_address(request.client.host).is_loopback
        host = request.url.hostname
        local_host = host == "localhost" or (host is not None and ip_address(host).is_loopback)
    except ValueError:
        local_peer = local_host = False
    forwarded = any(
        name == "forwarded" or name.startswith("x-forwarded-") for name in request.headers
    )
    if not local_peer or not local_host or forwarded:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "local_chat_only",
                "message": "Demo chat requires direct local access.",
            },
        )
