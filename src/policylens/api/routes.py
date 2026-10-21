"""HTTP contracts for authentication, JSON chat, readiness and deferred workflows."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from policylens.api.auth import login_user, refresh_tokens, register_user
from policylens.api.dependencies import get_current_user_id, get_qdrant, get_session
from policylens.api.schemas import (
    ChatErrorResponse,
    ChatRequest,
    ChatResponse,
    DocumentResponse,
    ErrorDetail,
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
from policylens.api.services import ChatServiceError, check_readiness, create_chat

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


@router.post(
    "/auth/register",
    tags=["Authentication"],
    status_code=201,
    response_model=UserResponse,
    responses={409: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def register(payload: RegisterRequest, session: Annotated[Session, Depends(get_session)]):
    """Register a user with a normalized email and an Argon2 password hash."""
    return register_user(session, payload)


@router.post(
    "/auth/login",
    tags=["Authentication"],
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def login(
    payload: LoginRequest, response: Response, session: Annotated[Session, Depends(get_session)]
):
    response.headers["Cache-Control"] = "no-store"
    return login_user(session, payload)


@router.post(
    "/auth/refresh",
    tags=["Authentication"],
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def refresh(
    payload: RefreshRequest, response: Response, session: Annotated[Session, Depends(get_session)]
):
    """Issue a new access token without extending or revoking the refresh token."""
    response.headers["Cache-Control"] = "no-store"
    return refresh_tokens(session, payload.refresh_token.get_secret_value())


@router.post(
    "/chat",
    tags=["Chat"],
    response_model=ChatResponse,
    responses={
        401: {"model": ErrorResponse, "description": "A valid access token is required"},
        503: {"model": ChatErrorResponse, "description": "A required dependency is unavailable"},
        500: {"model": ChatErrorResponse, "description": "Chat could not be completed"},
    },
)
def chat(
    payload: ChatRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[Session, Depends(get_session)],
):
    """Return and save one authenticated JSON exchange; history and memory are deferred."""
    try:
        return create_chat(session, payload.question, user_id)
    except ChatServiceError as exc:
        error = ChatErrorResponse(
            detail=ErrorDetail(code=exc.code, message=str(exc)), sources=exc.sources
        )
        return JSONResponse(
            status_code=500 if exc.code == "chat_failed" else 503,
            content=error.model_dump(mode="json"),
        )


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
