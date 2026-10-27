# PolicyLens — Citation-Grounded RAG for Regulatory Documents

PolicyLens is a citation-grounded Retrieval-Augmented Generation (RAG) project for regulatory documents.

> **Status:** Phase 3 retrieval experiments and a frozen hold-out evaluation are complete. Answer-generation quality is not measured by the retrieval results below.

---

## Current Foundation

- **Project Layout:** Modern Python `src/` layout (`src/policylens`).
- **Configuration:** Typed settings using `pydantic-settings` in `policylens.config`.
- **Code Quality:** Linting and formatting managed by Ruff.
- **Git Hooks:** Lightweight pre-commit checks for repository hygiene and code style.

---

## Local Setup

### 1. Install Package and Tooling

Install the package in editable mode with development dependencies:

```bash
pip install -e .[dev]
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

### 3. Verify Configuration

Print the active configuration:

```bash
python -m policylens.config
```

### 4. Run Code Quality Checks

Lint with Ruff:

```bash
ruff check .
```

Verify formatting:

```bash
ruff format --check .
```

Run unit tests:

```bash
pytest
```

---

## Retrieval Evaluation

The verified 60-question golden set was split into 48 development questions and 12 frozen hold-out questions. Hit@5, Recall@5, and MRR compare retrieved document/page pairs with gold sources; they exclude unanswerable questions and do not measure answer-generation correctness.

### Development ablation (41 answerable questions)

| Method | Hit@5 | Recall@5 | MRR | Rerank-only p50 (ms) |
| --- | ---: | ---: | ---: | ---: |
| [Dense](eval/results/retrieval_20261012T191839173509Z_af6558ebe4a5bce1f853b19340b8acdfe77ea87db78f6dd033f4fb3c73a9c58f.json) | 0.9268 | 0.8561 | 0.8862 | — |
| [BM25](eval/results/retrieval_bm25_20261014T095834356877Z_5047cbf0cbf3f1ac63547757db03dfa232d1159d1d06350c5abca79b22162fe8.json) | 0.9512 | 0.9049 | 0.8943 | — |
| [Hybrid RRF](eval/results/retrieval_hybrid_20261014T112307814856Z_d0bfed4a543cfd45b7657595060f953681e1ee0360400368f28007db81c1c702.json) | 0.9512 | 0.8927 | 0.8476 | — |
| [BM25 + BGE reranker](eval/results/retrieval_bm25_rerank_20261015T122408293824Z_4d93aa37e83e77ea2458a5c9e1a6760db1bea494d877701f961c1eac06d4cb9c.json) | 0.9512 | 0.9293 | 0.8951 | 2598.60 |
| [Hybrid + BGE reranker](eval/results/retrieval_hybrid_rerank_20261015T123138677133Z_49abbae93ee83b902bf70141a714133d964b26eab106e1e8fcf75314d36e286e.json) | 0.9512 | 0.9293 | 0.8951 | 2869.78 |

The frozen configuration was BM25 top 20 → `BAAI/bge-reranker-base` → top 5, with an abstention threshold of 0.60. On development questions, depth 20 improved Recall@5 over depth 10; depth 30 matched its recall but had lower MRR and higher reranking latency. BM25 and hybrid had equal reranked retrieval metrics, so the simpler BM25 path was selected; its measured reranking p50 was also lower. Chunk size, overlap, and final output depth were not tuned. The p50 values above cover reranking only, excluding first-stage retrieval and model loading.

### Frozen hold-out (selected configuration only)

| Answerable / unanswerable | Hit@5 | Recall@5 | MRR | Retrieval-only p50 (ms) | Rerank-only p50 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10 / 2 | 0.8000 | 0.8000 | 0.7333 | 30.09 | 3397.60 |

At the frozen 0.60 threshold, the evidence gate correctly refused 2/2 unanswerable questions, missed 0/2, wrongly refused 1/10 answerable questions, and correctly accepted 9/10. These are separate from the retrieval metrics, which use only the 10 answerable questions. The [saved hold-out report](eval/results/retrieval_bm25_rerank_holdout_20261015T182257754654Z_15f93293e5ee0669801fa0d69164bf1c69a9379717dfd17791ba89f2c65cef46.json) records the fixed run; the 12-question sample leaves substantial uncertainty about performance on new questions.

Metadata filters were verified functionally, not measured as a retrieval-quality ablation. Query rewriting was **not implemented** and has no measured result. Neither the retrieval scores nor the abstention counts establish that generated answers are correct.

## Prompt Injection and Privacy (Phase 4, Step 4.4)

Indirect prompt injection means instructions hidden in retrieved documents try to redirect the model. Both versioned prompts already label PDF text and metadata as untrusted, delimit the evidence, require grounded citations and allow a not-found response. Citation validation flags references absent from the supplied sources; it does not establish that claims are supported. PolicyLens has no model-controlled tools or agents; the main injection risk is a manipulated answer.

20 offline security tests and two live Groq tests passed; both prompt v1 and v2 resisted the tested injection. A separate one-page synthetic PDF passed through real parsing, chunking, isolated BM25 retrieval, BGE reranking and Groq generation: the answer retained the seven-calendar-day rule, cited page 1 and did not follow the malicious instruction. The temporary collection was deleted; production collections and PostgreSQL were unchanged. See [technical verification results](rag_notes.md#phase-4--step-44-prompt-injection-and-privacy-verification).

Project-owned diagnostic messages and saved RAGAS error details redact common email, phone, Indian PAN and Aadhaar formats. Existing RAG CLI failures already omit provider error details. User-facing answers, source evidence and evaluation answers/contexts remain unchanged; these artifacts can contain identifiers and are not anonymized exports. Third-party SDK logging is not globally filtered.

These are limited mitigations. Regexes can miss identifiers or hide nonpersonal numbers. Groq currently receives the rendered prompt in one user message, so role labels are text rather than enforced system-role separation. A single attack test cannot establish general resistance, and citation membership cannot guarantee factual correctness or complete security.

## Backend Service (Phase 5, Step 5.1)

With the `api` dependencies installed, start FastAPI from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn policylens.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Open [Swagger UI](http://127.0.0.1:8000/docs) to inspect exactly **13 documented API operations**. At Step 5.1, only `/health` and `/ready` were implemented; the other 11 operations returned HTTP 501 with a `not_implemented` error. `/health` checks process liveness without querying dependencies; `/ready` checks PostgreSQL and Qdrant connectivity.

Manual verification confirmed all 13 operations in Swagger, `/health` returning `{"status":"ok"}`, and `/ready` reporting both services healthy. After Qdrant was deliberately stopped, `/ready` reported Qdrant unavailable. Qdrant restarted successfully and readiness reported both services healthy again. `GET /sessions` returned the expected `not_implemented` error. These observations verify response JSON, not independent confirmation of HTTP status codes.

Step 5.1 offline verification: **8 focused API tests and 148 relevant regression tests passed**; Ruff lint and formatting checks passed.

Routers handle HTTP contracts, services coordinate application logic, and repositories perform database operations. This separation keeps business logic reusable and testable without coupling it to HTTP handlers.

## Functional JSON RAG Chat (Phase 5, Step 5.4)

`POST /chat` now accepts a question and returns a complete JSON response with the answer, supplied sources, citation-validation results, abstention decision, and generated session ID. It integrates the existing BM25 top-20 retrieval, BGE reranker top-5, 0.60 evidence gate, and Groq generation pipeline. Citation validation checks document/page membership in the supplied sources; it does not prove factual support. Completed exchanges persist a chat session and its user and assistant messages in PostgreSQL.

Step 5.4 originally used an opt-in local demo identity. Step 5.3 authentication below now replaces that bypass: `/chat` requires a bearer access token. Step 5.5 adds sessions and bounded conversation memory. SSE streaming and restricted-document RBAC remain deferred; five other workflow operations remain unimplemented.

Manual verification returned a grounded answer to a real regulatory question, with one valid citation and zero invalid citations. PostgreSQL contained both messages in the generated session. Qdrant unavailability produced a safe `retrieval_unavailable` response; restarting Qdrant restored `/ready` to healthy. These observations describe response content and database records, without independently verified HTTP status codes.

## Authentication and User Isolation (Phase 5, Step 5.3)

`POST /auth/register` accepts an email and a 12–128-character password, normalizes the email to lowercase, and stores an Argon2id hash with role `user`. The existing PostgreSQL unique index enforces case-insensitive email uniqueness. Duplicate registration returns a safe conflict error; login failures use the same message for unknown emails and incorrect passwords. Password hashes are never returned.

`POST /auth/login` returns `access_token`, `refresh_token`, and `token_type=bearer`. Access tokens expire after 15 minutes; refresh tokens expire after seven days. HS256 verification requires the issuer, audience, user ID, token type, issue/expiry times, and token identifier. `/auth/refresh` accepts a refresh token and returns a new access token alongside the same refresh token, retaining its original expiry. Access tokens cannot be used for refresh. There is **no logout, server-side revocation, or refresh-token rotation**: a stolen refresh token remains usable until expiry unless the user is deleted or the signing key changes.

`POST /chat` resolves the access token's user from PostgreSQL before running RAG, then saves both messages transactionally under that user. Step 5.5 supports an optional owned `session_id`; user identity is never accepted from the request body. The old demo flag no longer grants access; existing demo records are left untouched.

The API adds an `access_level=public` Qdrant pre-filter before BM25 ranking. Restricted, unknown, or missing access values are excluded. This relies on trusted scalar access labels: existing metadata records the regulatory corpus as public, but this step does not re-audit live payloads or implement restricted-document authorization. New restricted documents must not be mislabeled public during ingestion. Retrieval depths, reranking, prompts, and the 0.60 gate are unchanged.

For local Swagger verification, install the declared API dependencies, generate a process-local signing secret, and start the server (these commands do not change the configured Groq model):

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[api]"
$env:POLICYLENS_JWT_SECRET = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
.\.venv\Scripts\python.exe -m uvicorn policylens.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

The secret must represent 32 random bytes as 64 hex characters; missing, malformed, or obviously repetitive keys disable authentication with a safe error. Keep a stable secret in the deployment environment to retain tokens across restarts; never commit it. Use HTTPS for deployments carrying credentials or bearer tokens.

In [Swagger UI](http://127.0.0.1:8000/docs), register User A, log in, and paste the access token into **Authorize**. Call `/chat` with `{"question":"..."}` and verify `chat_sessions.user_id` matches the registered ID. Repeat for User B, verify missing/invalid bearer tokens are rejected, and try `/auth/refresh` with each token type.

Manual Swagger verification of registration, login, refresh, and authenticated chat passed, as reported locally. No additional API requests or automated tests were run for that documentation update. Refresh-token revocation, complex RBAC, email verification, password reset, and streaming remain deferred.

## Sessions and Conversation Memory (Phase 5, Step 5.5)

`POST /chat` creates a session when `session_id` is omitted or null; supplying an owned UUID appends to that session and returns the same ID. Missing and other users' sessions both return the same HTTP 404 error; malformed UUIDs fail request validation. Ownership is checked before loading history or calling the LLM, and checked again inside the append transaction. Both messages commit together; the original user question is stored unchanged.

Memory reads only the latest ten messages from the verified session, retains up to five complete user/assistant exchanges, and caps their serialized JSON at 8,000 characters. Newest complete exchanges are prioritized and kept in chronological order without truncating messages. If a recent exchange exceeds the budget, older exchanges are omitted too. First questions and sessions without usable history are not rewritten.

For follow-ups, the same cached Groq client rewrites the question into a standalone query using only that bounded conversation. History is treated as untrusted context, not regulatory evidence. The rewrite prompt also respects the existing 7,680-token input limit; failure, empty output, or unusable formatting falls back to the original question. The resolved question goes through the existing public-only BM25/reranker/gate/answer pipeline; citations are checked only against fresh retrieved evidence. Rewriting adds one best-effort LLM call and can resolve references incorrectly; it does not establish regulatory facts.

Both session endpoints require bearer authentication. `GET /sessions` lists at most 100 owned sessions, newest by creation time. `GET /sessions/{id}` returns an owned session and its latest 100 messages in chronological order. There is no pagination or summary memory. Send follow-ups sequentially: concurrent requests can read the same history snapshot even though each exchange is persisted atomically. No new tables, dependencies, or retrieval settings were introduced.

Manual Swagger verification passed for session reuse, message persistence, session listing, session retrieval, and cross-user ownership protection, as reported locally. No automated tests or additional API requests were run for this cleanup.

## Chat Rate Limiting (Phase 5, Step 5.7)

`POST /chat` admits at most **10 requests per authenticated user in a rolling 60-second window**. Identity comes from the verified access token and database user lookup; changing tokens or sessions does not reset a user's allowance. Excess requests return HTTP 429 with `detail.code=rate_limit_exceeded` and an integer `Retry-After` header in seconds. Rejection happens before session history, rewriting, retrieval, model calls, or message writes; authentication still performs its existing database lookup.

Admitted attempts count even if later validation or processing fails, including session 404s. Rejected attempts do not extend the window. `/health`, `/ready`, and other routes are not rate-limited. Counters use a lock and monotonic time in application memory, expire when idle, and reset on restart. They are **not shared across worker processes or replicas**; this implementation is for a single-process MVP.

Manual verification is pending. To check through Swagger without spending LLM quota, restart one server process, authorize a user, and submit a valid question with a nonexistent, valid-format session UUID ten times within 60 seconds. Those requests return 404; the next returns 429 with `Retry-After`. Wait the indicated delay and retry. A second user's allowance is independent, and health/readiness remain accessible. No automated tests or live API requests were run during implementation.

## Optional Langfuse Tracing (Phase 6, Step 6.1)

Install `python -m pip install -e ".[tracing]"`. The optional extra selects SDK v4.7+ on Python 3.10 or v5.0.4+ on Python 3.11+, following [Langfuse's compatibility guidance](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v4-to-v5). Use Langfuse Cloud, or a self-hosted version compatible with your SDK (v5 requires server v4.59.0+). Set `POLICYLENS_LANGFUSE_ENABLED=true`, `POLICYLENS_LANGFUSE_PUBLIC_KEY`, `POLICYLENS_LANGFUSE_SECRET_KEY`, and the matching regional/self-hosted `POLICYLENS_LANGFUSE_BASE_URL` in your local environment; examples are in `.env.example`. Never commit real keys. Tracing is disabled by default; missing configuration, a missing SDK, or telemetry failures leave normal chat running. Restart after configuration changes. Export is asynchronous and uses the SDK's background batching and shutdown handling, without per-request flushing.

Each `POST /chat` creates one root observation when tracing is available, tagged with the database-validated user role and prompt `v1`. Requests rejected before authentication use an `unauthenticated` role tag. Only three child observations are instrumented: **retrieval**, **reranking**, and **llm_generation**. Refusals and failures can have fewer children because skipped work is not executed. Health, readiness, authentication and session endpoints are not traced.

Traces include redacted original/resolved queries and answers, ordered document IDs, canonical chunk IDs (`doc_id:chunk_index`, not Qdrant point UUIDs), pages, BM25/reranker scores, actually supplied source identifiers, abstention/citation statistics, HTTP status, request/stage latencies, and a deterministic SHA-256 configuration hash. The non-secret configuration includes retrieval limits, models, public-only restriction, threshold, history/token budgets, chunk settings and both prompt-file hashes; it is not a complete Qdrant snapshot. Provider token counts are recorded when Groq supplies them, separately for rewriting and answer generation. Encoded prompt-text counts use the existing `o200k_harmony` counter and exclude provider chat framing; they are separate from provider-reported usage.

No user/session IDs, emails, auth headers, full conversation history, raw prompts, retrieved chunk text, or raw exception messages are deliberately captured. Free text reuses personal-identifier redaction plus credential/token/UUID masking, which can miss unusual formats and can hide legitimate identifiers. Structured document/chunk IDs remain available for source inspection. Only explicitly named PolicyLens SDK observations are exported; no automatic LangChain or Groq callbacks are installed. Tracing sends redacted telemetry to your configured Langfuse deployment, so review it before using sensitive queries.

For manual verification, enable tracing, restart FastAPI, authorize in Swagger, and submit one normal regulatory question. In Langfuse, inspect the root and its three executed stages: compare the twenty BM25 candidates, five reranked chunks, supplied sources, scores, token counts and answer against the source PDFs. Valid citations establish membership, not factual support. Try an abstaining query and an invalid session to inspect skipped stages/errors. Check that a query containing a synthetic email or `password=synthetic-value` is redacted, then disable tracing or use an unavailable Langfuse URL and confirm chat still works. Authentication/rate-limit rejections contain status metadata, not query bodies or RAG spans. Manual verification is pending; no automated tests or live service requests were run during implementation.

## Stage Latency and Estimated Cost (Phase 6, Step 6.2)

Completed `/chat` exchanges, including abstentions, write one PostgreSQL `query_logs` row independently of Langfuse. Existing message transactions are unchanged; logging uses a separate transaction and a logging failure leaves the saved chat response intact, with a generic warning. Failed/rejected chats are excluded. Apply the additive migration manually before verification: `.\.venv\Scripts\python.exe -m alembic upgrade head`. Historical records keep null values for the new `model` and `token_usage` fields.

`latency_per_stage` stores milliseconds for `total`, `rewrite`, `retrieval`, `reranking`, and `llm_generation`; skipped stages are `0`. Rewrite measures the LLM call, while retrieval/reranking/generation reuse Step 6.1 timings. Total covers middleware entry through response preparation after message persistence, excluding the query-log write itself and network delivery. Initialization and other overhead can make total exceed the stage sum. Existing Langfuse traces retain their three main child observations.

`tokens_in`/`tokens_out` sum actual Groq response usage across attempted rewrite and generation calls. Per-call usage is retained in `token_usage`; an incomplete count makes the corresponding total unknown/null. Local prompt-text token counts remain separate in traces and are never treated as billed usage. With no LLM call, totals are zero. No conversation or prompt text is added to PostgreSQL query logs.

Cost is an **estimate**, not an invoice: `(input tokens × input USD price + output tokens × output USD price) / 1,000,000`, including rewrite usage. Configure `POLICYLENS_LLM_PRICING_MODEL` to exactly match the active Groq model, plus `POLICYLENS_LLM_INPUT_PRICE_PER_MILLION` and `POLICYLENS_LLM_OUTPUT_PRICE_PER_MILLION` from the applicable provider tariff, then restart. Missing/mismatched pricing or incomplete usage gives null cost; no-call requests cost zero only when pricing is configured. The row retains the applied prices, and cost is stored to eight decimal places. Discounts, caching tariffs and provider billing adjustments are not modeled.

Run `.\.venv\Scripts\python.exe scripts/query_log_report.py` for sample counts, per-stage p50/p95, the stage with the highest p50, and average estimated cost over rows with known costs. p50 describes typical latency; p95 exposes the slow tail that an average can hide. The report uses inclusive percentile interpolation; small samples are uncertain and do not establish stable production performance. Manual verification and identification of the measured dominant stage remain pending; no chat requests or migrations were executed during implementation.
