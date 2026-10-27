"""Optional native Langfuse observations for chat; no automatic payload capture."""

import hashlib
import json
import re
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from policylens.config import get_settings
from policylens.privacy import redact_for_tracing

_request: ContextVar[dict[str, Any] | None] = ContextVar("policylens_trace", default=None)
_generation: ContextVar[Any] = ContextVar("policylens_generation", default=None)
_OBSERVATIONS = {"POST /chat", "retrieval", "reranking", "llm_generation"}


@lru_cache(maxsize=1)
def _client():
    try:
        settings = get_settings()
        if not (
            settings.langfuse_enabled
            and settings.langfuse_public_key
            and settings.langfuse_secret_key
        ):
            return None
        from langfuse import Langfuse
        from langfuse.span_filter import is_langfuse_span

        return Langfuse(
            public_key=settings.langfuse_public_key.get_secret_value(),
            secret_key=settings.langfuse_secret_key.get_secret_value(),
            base_url=settings.langfuse_base_url,
            environment=settings.environment,
            debug=False,
            timeout=2,
            should_export_span=lambda span: is_langfuse_span(span) and span.name in _OBSERVATIONS,
        )
    except Exception:
        return None


def update_observation(observation, **fields: Any) -> None:
    if observation is not None:
        with suppress(Exception):
            observation.update(**fields)


@lru_cache(maxsize=1)
def _configuration() -> dict[str, Any]:
    from policylens.api.services import _HISTORY_CHARACTERS, _HISTORY_EXCHANGES
    from policylens.rag import _CANDIDATE_K, _FINAL_K, _MAX_COMPLETION_TOKENS, _MAX_PROMPT_TOKENS
    from policylens.reranker import ABSTENTION_THRESHOLD, MODEL_NAME

    settings = get_settings()
    prompt_dir = Path(__file__).resolve().parents[2] / "prompts"
    return {
        "method": "bm25_rerank",
        "collection": settings.bm25_collection,
        "bm25_model": "qdrant/bm25",
        "sparse_vector": "bm25",
        "modifier": "idf",
        "candidate_k": _CANDIDATE_K,
        "final_k": _FINAL_K,
        "reranker_model": MODEL_NAME,
        "abstention_threshold": ABSTENTION_THRESHOLD,
        "public_only": True,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "temperature": 0,
        "max_completion_tokens": _MAX_COMPLETION_TOKENS,
        "max_prompt_tokens": _MAX_PROMPT_TOKENS,
        "prompt_encoding": "o200k_harmony",
        "prompt_version": "v1",  # The API keeps build_rag_chain's existing default.
        "prompt_hashes": {
            version: hashlib.sha256((prompt_dir / f"answer_{version}.txt").read_bytes()).hexdigest()
            for version in ("v1", "v2")
        },
        "history_exchanges": _HISTORY_EXCHANGES,
        "history_characters": _HISTORY_CHARACTERS,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
    }


@contextmanager
def chat_trace():
    """One root per HTTP chat request; telemetry errors never consume application errors."""
    root = manager = state = token = None
    started = perf_counter()
    try:
        client = _client()
        if client is not None:
            configuration = _configuration()
            digest = hashlib.sha256(
                json.dumps(configuration, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            manager = client.start_as_current_observation(
                name="POST /chat",
                trace_context={"trace_id": uuid4().hex},
                end_on_exit=False,
                metadata={
                    "configuration": configuration,
                    "configuration_hash": digest,
                    "prompt_version": "v1",
                },
            )
            root = manager.__enter__()
            state = {"root": root, "role": "unauthenticated", "latencies": {}, "usage": {}}
            token = _request.set(state)
    except Exception:
        pass
    try:
        yield root
    except Exception as exc:
        update_observation(root, level="ERROR", status_message=type(exc).__name__)
        raise
    finally:
        if state is not None:
            with suppress(Exception):
                from langfuse import propagate_attributes

                with propagate_attributes(tags=[f"role:{state['role']}", "prompt:v1"]):
                    pass
            update_observation(
                root,
                metadata={
                    "user_role": state["role"],
                    "request_latency_ms": (perf_counter() - started) * 1000,
                    "stage_latency_ms": state["latencies"],
                    "provider_token_usage": state["usage"],
                },
            )
        if root is not None:
            with suppress(Exception):
                root.end()
            # Do not pass provider/application exceptions to SDK auto-error capture.
            with suppress(Exception):
                manager.__exit__(None, None, None)
        if token is not None:
            _request.reset(token)


def record_user_role(role: str) -> None:
    state = _request.get()
    if state is not None:
        state["role"] = (
            role if isinstance(role, str) and re.fullmatch(r"[a-z_-]{1,32}", role) else "other"
        )


def record_query(question: str, *, retrieval: bool = False) -> None:
    state = _request.get()
    if state is not None:
        with suppress(Exception):
            redacted = redact_for_tracing(question)
            if retrieval:
                update_observation(state["root"], metadata={"retrieval_query": redacted})
            else:
                update_observation(state["root"], input={"query": redacted})


@contextmanager
def trace_stage(name: str, **fields: Any):
    state = _request.get()
    if state is None:
        yield None
        return
    span = None
    started = perf_counter()
    try:
        from langfuse import propagate_attributes

        with propagate_attributes(tags=[f"role:{state['role']}", "prompt:v1"]):
            span = state["root"].start_observation(name=name, **fields)
    except Exception:
        pass
    token = _generation.set({"observation": span}) if name == "llm_generation" else None
    try:
        yield span
    except Exception as exc:
        update_observation(span, level="ERROR", status_message=type(exc).__name__)
        raise
    finally:
        latency = (perf_counter() - started) * 1000
        state["latencies"][name] = latency
        update_observation(span, metadata={"latency_ms": latency})
        if span is not None:
            with suppress(Exception):
                span.end()
        if token is not None:
            _generation.reset(token)


def record_candidates(span, candidates: list[dict[str, Any]]) -> None:
    if span is not None:
        with suppress(Exception):
            rows = []
            for rank, chunk in enumerate(candidates, 1):
                doc_id = chunk["metadata"].get("doc_id")
                index = chunk["metadata"].get("chunk_index")
                rows.append(
                    {
                        "rank": rank,
                        "doc_id": doc_id,
                        "chunk_index": index,
                        "chunk_id": f"{doc_id}:{index}"
                        if doc_id is not None and index is not None
                        else None,
                        "page": chunk.get("page"),
                        "retrieval_score": chunk.get("score"),
                        "rerank_score": chunk.get("rerank_score"),
                    }
                )
            update_observation(span, output=rows)


def record_usage(usage: Any) -> None:
    state = _request.get()
    if state is not None:
        with suppress(Exception):
            values = {
                key: getattr(usage, field, None)
                for key, field in (
                    ("input", "prompt_tokens"),
                    ("output", "completion_tokens"),
                    ("total", "total_tokens"),
                )
            }
            values = {
                key: value for key, value in values.items() if type(value) is int and value >= 0
            }
            generation = _generation.get()
            state["usage"]["generation" if generation is not None else "rewrite"] = values or None
            update_observation(
                generation["observation"] if generation is not None else None,
                usage_details=values or None,
            )


def record_answer(result: dict[str, Any]) -> None:
    state = _request.get()
    if state is not None:
        with suppress(Exception):
            validation = result["citation_validation"]
            update_observation(
                state["root"],
                output={
                    "answer": redact_for_tracing(result["answer"]),
                    "abstained": result["abstained"],
                    "citation_precision": validation["citation_precision"],
                    "invalid_citation_count": len(validation["invalid_citations"]),
                    "supplied_sources": [
                        {key: source.get(key) for key in ("doc_id", "chunk_index", "page")}
                        for source in result["sources"]
                    ],
                },
            )
