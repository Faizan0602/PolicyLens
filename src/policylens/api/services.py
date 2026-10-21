"""Coordinate readiness and chat without HTTP response handling."""

from functools import lru_cache
from typing import Any
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.common.client_exceptions import QdrantException
from qdrant_client.http.exceptions import ApiException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from policylens.api.schemas import ChatResponse, ReadyResponse
from policylens.config import get_settings
from policylens.db.repository import check_postgres, check_qdrant, save_chat_exchange


class ChatServiceError(Exception):
    """A safe failure description and any sources already supplied to generation."""

    def __init__(self, code: str, message: str, sources: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.code = code
        self.sources = sources or []


@lru_cache(maxsize=1)
def _chat_chain():
    # Import and initialize only when an enabled local chat request is made.
    from policylens.rag import build_rag_chain

    if get_settings().llm_provider.strip().lower() != "groq":
        raise ValueError("Local chat requires the configured Groq provider")
    return build_rag_chain()


def create_chat(session: Session, question: str) -> ChatResponse:
    try:
        chain = _chat_chain()
    except Exception:
        raise ChatServiceError(
            "generation_unavailable", "Answer generation is unavailable."
        ) from None

    try:
        result = chain.invoke(question)
        response = ChatResponse(session_id=uuid4(), **result)
    except (ApiException, QdrantException):
        raise ChatServiceError(
            "retrieval_unavailable", "Document retrieval is temporarily unavailable."
        ) from None
    except Exception as exc:
        sources = getattr(exc, "policylens_sources", None)
        if sources is not None:
            raise ChatServiceError(
                "generation_unavailable", "Answer generation is temporarily unavailable.", sources
            ) from None
        raise ChatServiceError("chat_failed", "The chat request could not be completed.") from None

    # No database connection/transaction is held while retrieval or generation runs.
    try:
        save_chat_exchange(
            session,
            response.session_id,
            question,
            response.answer,
            response.citation_validation["valid_citations"],
        )
    except SQLAlchemyError:
        raise ChatServiceError(
            "persistence_unavailable",
            "The exchange could not be confirmed as saved.",
            result["sources"],
        ) from None
    except Exception:
        raise ChatServiceError(
            "chat_failed", "The chat request could not be completed.", result["sources"]
        ) from None
    return response


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
