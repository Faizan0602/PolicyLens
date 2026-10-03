# PolicyLens — Citation-Grounded RAG for Regulatory Documents

PolicyLens is an upcoming citation-grounded Retrieval-Augmented Generation (RAG) system for regulatory documents.

> **Status:** The project is being built phase-by-phase following a strict roadmap. It is currently at **Phase 0 (Foundations and Setup), Step 0.2A (Project Structure, Configuration, and Local Development Tooling)**. Ingestion, retrieval, RAG, and serving pipelines are not yet implemented.

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
