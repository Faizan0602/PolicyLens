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
