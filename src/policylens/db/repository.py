"""Read-only connectivity probes; no registry or schema modifications."""

from qdrant_client import QdrantClient
from sqlalchemy import text
from sqlalchemy.orm import Session


def check_postgres(session: Session) -> None:
    session.execute(text("SELECT 1"))


def check_qdrant(client: QdrantClient) -> None:
    client.get_collections()
