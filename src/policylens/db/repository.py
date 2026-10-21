"""Database connectivity, user lookup and atomic exchange persistence."""

from uuid import UUID

from qdrant_client import QdrantClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from policylens.db.models import ChatSession, Message, User


def check_postgres(session: Session) -> None:
    session.execute(text("SELECT 1"))


def check_qdrant(client: QdrantClient) -> None:
    client.get_collections()


def find_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(func.lower(User.email) == email))


def find_user_by_id(session: Session, user_id: UUID) -> User | None:
    return session.get(User, user_id)


def insert_user(session: Session, email: str, password_hash: str) -> User:
    with session.begin():
        user = User(email=email, password_hash=password_hash, role="user")
        session.add(user)
        session.flush()
        # Preserve returned scalar fields without a post-commit database read.
        session.expunge(user)
    return user


def save_chat_exchange(
    session: Session,
    session_id: UUID,
    question: str,
    answer: str,
    citations: list[dict],
    *,
    user_id: UUID,
) -> None:
    """Commit a fresh session and two messages for the authenticated user together."""
    with session.begin():
        session.add(ChatSession(id=session_id, user_id=user_id, title=question.strip()[:120]))
        session.flush()
        session.add_all(
            [
                Message(session_id=session_id, role="user", content=question, citations=[]),
                Message(
                    session_id=session_id, role="assistant", content=answer, citations=citations
                ),
            ]
        )
