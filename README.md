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

Chat is a local-development-only demo, disabled by default. It requires `POLICYLENS_DEMO_CHAT_ENABLED=true`, `POLICYLENS_ENVIRONMENT=development`, and direct loopback access. SSE streaming is intentionally deferred; authentication/RBAC and conversation memory are also deferred. The other ten workflow operations remain unimplemented.

Manual verification returned a grounded answer to a real regulatory question, with one valid citation and zero invalid citations. PostgreSQL contained both messages in the generated session. Qdrant unavailability produced a safe `retrieval_unavailable` response; restarting Qdrant restored `/ready` to healthy. These observations describe response content and database records, without independently verified HTTP status codes.
