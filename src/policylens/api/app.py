"""Create the API without connecting to services or loading models at import time."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient

from policylens.api.auth import AuthError
from policylens.api.routes import router
from policylens.config import get_settings
from policylens.db.session import get_engine, get_session_factory


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = get_engine(
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=3000"},
        pool_timeout=3,
    )
    try:
        key = settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
        client = QdrantClient(
            url=settings.qdrant_url, api_key=key, timeout=3, check_compatibility=False
        )
        try:
            app.state.session_factory = get_session_factory(engine)
            app.state.qdrant_client = client
            yield
        finally:
            client.close()
    finally:
        engine.dispose()


def create_app() -> FastAPI:
    """Register authentication, JSON chat, health and deferred workflow contracts."""
    app = FastAPI(
        title="PolicyLens API",
        version="0.1.0",
        description=(
            "Authentication, JSON /chat, health and readiness are implemented. "
            "Chat requires a bearer access token and uses public documents only. "
            "Streaming and memory are deferred; other operations return HTTP 501."
        ),
        lifespan=lifespan,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )

    @app.exception_handler(AuthError)
    async def auth_error(request: Request, exc: AuthError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": exc.code, "message": str(exc)}},
            headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None,
        )

    app.include_router(router)
    return app
