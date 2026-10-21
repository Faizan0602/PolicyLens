"""Database connectivity probes and atomic local-demo exchange persistence."""

from uuid import NAMESPACE_URL, UUID, uuid5

from qdrant_client import QdrantClient
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from policylens.db.models import ChatSession, Message, User

_DEMO_USER_ID = uuid5(NAMESPACE_URL, "policylens:local-demo-user")
_DEMO_EMAIL = "local-demo@policylens.invalid"
# A disabled-account marker, not a password or usable password hash.
_DISABLED_LOGIN_MARKER = "!disabled-local-demo"


def check_postgres(session: Session) -> None:
    session.execute(text("SELECT 1"))


def check_qdrant(client: QdrantClient) -> None:
    client.get_collections()


def save_chat_exchange(
    session: Session,
    session_id: UUID,
    question: str,
    answer: str,
    citations: list[dict],
) -> None:
    """Commit the demo identity, fresh session and two complete messages together."""
    with session.begin():
        session.execute(
            insert(User)
            .values(
                id=_DEMO_USER_ID,
                email=_DEMO_EMAIL,
                password_hash=_DISABLED_LOGIN_MARKER,
                role="user",
            )
            .on_conflict_do_nothing(index_elements=[User.id])
        )
        user = session.get(User, _DEMO_USER_ID)
        if (
            user is None
            or user.email != _DEMO_EMAIL
            or user.password_hash != _DISABLED_LOGIN_MARKER
            or user.role != "user"
        ):
            raise ValueError("Reserved demo identity does not match the disabled demo account")
        session.add(ChatSession(id=session_id, user_id=user.id, title=question.strip()[:120]))
        session.flush()
        session.add_all(
            [
                Message(session_id=session_id, role="user", content=question, citations=[]),
                Message(
                    session_id=session_id, role="assistant", content=answer, citations=citations
                ),
            ]
        )
