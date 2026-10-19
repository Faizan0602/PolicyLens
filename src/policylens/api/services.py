"""Coordinate backend readiness without depending on HTTP response handling."""

from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from policylens.api.schemas import ReadyResponse
from policylens.db.repository import check_postgres, check_qdrant


def check_readiness(session: Session, client: QdrantClient) -> ReadyResponse:
    dependencies = {}
    for name, check, resource in (
        ("postgresql", check_postgres, session),
        ("qdrant", check_qdrant, client),
    ):
        try:
            check(resource)
        except Exception:
            # Probe failures are reported without exposing SDK or credential details.
            dependencies[name] = "unavailable"
        else:
            dependencies[name] = "ok"
    status = "ready" if all(value == "ok" for value in dependencies.values()) else "not_ready"
    return ReadyResponse(status=status, dependencies=dependencies)
