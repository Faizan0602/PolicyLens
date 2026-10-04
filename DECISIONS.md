# Architecture & Technical Decisions

This document records architectural, tooling, and design decisions made throughout the lifecycle of PolicyLens.

---

## Decision 001: Python Packaging and Repository Foundation (Phase 0, Step 0.2A)

### Status
Accepted

### Context
PolicyLens requires a maintainable, reproducible, and production-ready Python project foundation prior to building ingestion, retrieval, and evaluation pipelines.

### Decisions Made

1. **Packaging Structure: `src/` Layout**
   - Adopted a modern `src/policylens` layout configured via `pyproject.toml` (PEP 517/518/621).
   - *Rationale:* Prevents unintentional imports of the local working directory during testing, ensures tests run against installed package artifacts, and guarantees clean packaging boundaries.

2. **Typed Configuration: `pydantic-settings`**
   - Centralized application configuration in `policylens.config.Settings` backed by `pydantic-settings`.
   - *Rationale:* Provides type validation, automatic environment variable reading (`POLICYLENS_` prefix), `.env` file support, and an extendable schema for future components. Includes safe dump/string representations to prevent inadvertent secret leakage.

3. **Environment Management**
   - Provided `.env.example` with safe placeholder defaults.
   - Configured `.gitignore` to prevent any `.env` file from being tracked or committed.

4. **Linting and Formatting: Ruff**
   - Standardized on Ruff for both linting and formatting via `pyproject.toml`.
   - *Rationale:* Replaces multiple legacy tools (flake8, black, isort) with a single, fast tool that maintains strict code quality and consistent formatting without excessive rule friction.

5. **Local Git Hygiene: Pre-Commit Hooks**
   - Configured `.pre-commit-config.yaml` with standard repository hygiene hooks (trailing whitespace, YAML validation, EOF fixes) and Ruff lint/format integration.
   - *Rationale:* Enforces clean code standards before code enters the repository.

---

## Decision 002: LLM Interface, Embedding Model Selection & Query Instructions (Phase 0, Step 0.3)

### Status
Accepted

### Context
PolicyLens requires an extensible foundation for generating text completions and dense semantic representations without hardcoding vendor-specific libraries or models into future ingestion and retrieval pipelines.

### Decisions Made

1. **Provider-Agnostic LLM Factory (`get_llm`)**
   - Application logic consumes a generic `LLMClient` protocol rather than directly importing provider-specific clients.
   - Provider selection is driven 100% via environment variables (`POLICYLENS_LLM_PROVIDER`, `POLICYLENS_LLM_MODEL`).
   - Supports `mock` (deterministic simulated responses for offline testing and CI), `gemini`/`google`, and `openai`.

2. **Embedding Model Selection (`BAAI/bge-small-en-v1.5`)**
   - Standardized on `BAAI/bge-small-en-v1.5` loaded through `sentence-transformers`.
   - *Rationale:* Produces compact 384-dimensional embeddings with fast CPU/GPU inference, minimal memory footprint, and strong performance across retrieval and semantic textual similarity (STS) benchmarks.

3. **Query Instruction Policy (BGE v1.5 Model Card Findings)**
   - Analysis of the official BAAI model card and technical reports reveals:
     - **General usage:** Unlike earlier BGE releases, `v1.5` was tuned to function effectively without instructions, exhibiting only minor degradation when omitted.
     - **Asymmetric Retrieval (Short Query to Long Document):** When searching passages using short user queries, the model card specifically recommends prepending the instruction:
       `"Represent this sentence for searching relevant passages: "`
     - **Corpus / Passages:** Documents and corpus passages must **never** include the instruction.
     - **Symmetric Sentence Similarity:** For pairwise sentence comparison (such as regulatory circular semantic matching), no instructions should be added to either sentence.
   - *PolicyLens Implementation Policy:* When online retrieval is implemented in Phase 2, queries will prepend the instruction, while document ingestion in Phase 1 will index raw passages without instructions.

4. **Transparent Manual Similarity Computation**
   - Similarity calculations in this foundation step explicitly implement cosine similarity using standard NumPy operations (`u . v / (||u|| * ||v||)`) rather than relying on opaque library helpers, ensuring mathematical verification of embedding behavior.
