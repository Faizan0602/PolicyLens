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
