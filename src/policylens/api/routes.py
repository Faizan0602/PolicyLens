"""HTTP contracts; only liveness and readiness execute application logic."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from policylens.api.dependencies import get_qdrant, get_session
from policylens.api.schemas import (
    ChatRequest,
    ChatResponse,
    DocumentResponse,
    ErrorResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    IngestRequest,
    JobResponse,
    LoginRequest,
    ReadyResponse,
    RefreshRequest,
    RegisterRequest,
    SessionDetailResponse,
    SessionResponse,
    TokenResponse,
    UserResponse,
)
from policylens.api.services import check_readiness

router = APIRouter()
pending = APIRouter(
    responses={501: {"model": ErrorResponse, "description": "Business functionality pending"}}
)


def not_implemented() -> NoReturn:
    raise HTTPException(
        status_code=501,
        detail={
            "code": "not_implemented",
            "message": "This workflow is not implemented in Step 5.1.",
        },
    )


@pending.post(
    "/auth/register", tags=["Authentication"], status_code=201, response_model=UserResponse
)
def register(payload: RegisterRequest):
    """Planned user registration; currently returns HTTP 501."""
    not_implemented()


@pending.post("/auth/login", tags=["Authentication"], response_model=TokenResponse)
def login(payload: LoginRequest):
    """Planned login; currently returns HTTP 501."""
    not_implemented()


@pending.post("/auth/refresh", tags=["Authentication"], response_model=TokenResponse)
def refresh(payload: RefreshRequest):
    """Planned token refresh; currently returns HTTP 501."""
    not_implemented()


@pending.post(
    "/chat",
    tags=["Chat"],
    response_model=ChatResponse,
    responses={
        200: {
            "description": "Planned answer/source payload; SSE transport is not implemented",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        }
    },
)
def chat(payload: ChatRequest):
    """Planned chat with SSE and sources; currently returns HTTP 501 without generating."""
    not_implemented()


@pending.get("/sessions", tags=["Sessions"], response_model=list[SessionResponse])
def list_sessions():
    """Planned session listing; currently returns HTTP 501."""
    not_implemented()


@pending.get("/sessions/{id}", tags=["Sessions"], response_model=SessionDetailResponse)
def get_session_detail(id: UUID):
    """Planned session history; currently returns HTTP 501."""
    not_implemented()


@pending.post("/feedback", tags=["Feedback"], status_code=201, response_model=FeedbackResponse)
def submit_feedback(payload: FeedbackRequest):
    """Planned feedback submission; currently returns HTTP 501."""
    not_implemented()


@pending.get("/documents", tags=["Documents"], response_model=list[DocumentResponse])
def list_documents():
    """Planned document listing; currently returns HTTP 501."""
    not_implemented()


@pending.get(
    "/documents/{id}/pdf",
    tags=["Documents"],
    response_class=Response,
    responses={
        200: {
            "description": "Planned PDF download; not implemented",
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
def download_pdf(id: UUID):
    """Planned document download; currently returns HTTP 501."""
    not_implemented()


@pending.post("/admin/ingest", tags=["Administration"], status_code=202, response_model=JobResponse)
def ingest(payload: IngestRequest):
    """Planned ingestion submission; currently returns HTTP 501 without creating a job."""
    not_implemented()


@pending.get("/admin/jobs/{id}", tags=["Administration"], response_model=JobResponse)
def get_job(id: UUID):
    """Planned job status; currently returns HTTP 501."""
    not_implemented()


@router.get("/health", tags=["System"], response_model=HealthResponse)
def health():
    return HealthResponse()


@router.get(
    "/ready",
    tags=["System"],
    response_model=ReadyResponse,
    responses={503: {"model": ReadyResponse}},
)
def ready(
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    client: Annotated[QdrantClient, Depends(get_qdrant)],
):
    """Check database connectivity only; corpus completeness and LLM access are not checked."""
    result = check_readiness(session, client)
    if result.status == "not_ready":
        response.status_code = 503
    return result


router.include_router(pending)
