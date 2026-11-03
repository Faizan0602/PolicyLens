# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

FROM python-base AS builder

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY src/ ./src/
# CPU wheels avoid bundling CUDA libraries on a CPU hosting service.
RUN python -m pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --no-cache-dir ".[api,groq]" \
    && python -m pip check

FROM python-base AS runtime

# Required by the CPU inference libraries; no compiler is kept in the image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 policylens \
    && useradd --uid 10001 --gid policylens --create-home policylens \
    && install -d -o policylens -g policylens \
        /home/policylens/.cache \
        /home/policylens/.cache/huggingface /home/policylens/.cache/tiktoken

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    HOME=/home/policylens \
    XDG_CACHE_HOME=/home/policylens/.cache \
    HF_HOME=/home/policylens/.cache/huggingface \
    TIKTOKEN_CACHE_DIR=/home/policylens/.cache/tiktoken \
    PYTHONPATH=/app/src \
    POLICYLENS_ENVIRONMENT=production \
    PORT=8000

COPY --from=builder /opt/venv /opt/venv
# Source imports preserve Path(__file__).parents[2] / "prompts" in the app.
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY alembic.ini ./
COPY alembic/ ./alembic/

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + (os.environ.get('PORT') or '8000') + '/health', timeout=3).close()"]

# Supply POLICYLENS_DATABASE_URL with postgresql+psycopg2:// at runtime.
# Run migrations separately as a release task: python -m alembic upgrade head.
CMD ["sh", "-c", "exec python -m uvicorn policylens.api.app:create_app --factory --host 0.0.0.0 --port \"${PORT:-8000}\""]
