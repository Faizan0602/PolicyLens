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

---

## Decision 003: PDF Parser Selection (PyMuPDF) (Phase 1, Step 1.1)

### Status
Accepted

### Context
PolicyLens requires a reliable PDF parser capable of extracting text while preserving structural layout, tracking page numbers, and remaining performant over large regulatory corpuses.

### Decisions Made
- **Decision:** Selected `PyMuPDF` (`fitz`) as the core PDF parsing engine.
- **Reasoning:** PyMuPDF is backed by a highly optimized C/C++ engine (MuPDF), making it exceptionally fast. It extracts text quickly, though like any PDF parser, it does not guarantee perfectly preserved reading order or layout for all documents. It inherently supports tracking page numbers and allows lightweight heuristics like text-density checks to identify scanned pages without invoking heavy OCR immediately.
- **Trade-offs and Limitations:** While PyMuPDF can support OCR through optional Tesseract integration, our current pipeline does not implement OCR, meaning it cannot read text embedded inside images (scanned documents). Furthermore, its AGPL licensing requires careful consideration for distribution and deployment depending on whether the software is used as an internal service or a distributed commercial product.

---

## Decision 004: Structure-Aware Chunking (Phase 1, Step 1.4)

### Status
Accepted

### Context
Standard recursive chunking often blindly slices text at character limits, severing a paragraph from its critical section heading (e.g., separating "Banks must maintain 7% capital" from "CHAPTER II: CAPITAL ADEQUACY").

### Decisions Made
- **Decision:** Implemented a two-pass "structure-aware" chunking strategy combining regex-based heading detection with LangChain's `RecursiveCharacterTextSplitter`.
- **Reasoning:** In legal and regulatory documents, a section's heading is the most vital piece of context. By first splitting the document into logical sections and storing the "active heading", we can prepend or attach that heading to every downstream chunk. This ensures the embedding model and the final LLM always know exactly which section a fragmented paragraph belongs to, providing better semantic context to downstream retrieval steps.
- **Trade-offs and Limitations:** Heading detection relies on heuristic rules and regular expressions, meaning highly unconventional or poorly formatted headings might be missed. Additionally, pages like Tables of Contents require special filter logic to prevent them from corrupting the "active heading" state of subsequent pages.

---

## Decision 005: Embedding Model Selection (BAAI/bge-small-en-v1.5) (Phase 1, Step 1.5)

### Status
Accepted

### Context
PolicyLens needs a dense vector representation model to convert text chunks into searchable mathematical arrays.

### Decisions Made
- **Decision:** Selected `BAAI/bge-small-en-v1.5` run locally via `sentence-transformers`.
- **Reasoning:** This model produces compact 384-dimensional vectors. This represents a calculated trade-off favoring minimal memory footprint, lower deployment cost, and faster CPU/GPU inference speed while maintaining sufficient embedding quality for our domain. Running it locally removes network latency and API costs associated with closed-source embeddings.
- **Trade-offs and Limitations:** The model card recommends prepending a specific instruction prompt (`"Represent this sentence for searching relevant passages: "`) to user queries for some asymmetric retrieval use cases, though it is not an unconditional strict requirement. Currently, our initial `search_chunks` implementation does not automatically prepend this instruction. It is an English-only model.

---

## Decision 006: Canonical 14-Field Metadata Schema (Phase 1, Step 1.4)

### Status
Accepted

### Context
A chunk of text is useless if we don't know where it came from, who issued it, or when it became effective. RAG systems often suffer from "context collapse" if metadata isn't strictly tracked.

### Decisions Made
- **Decision:** Designed a strict 14-field Pydantic schema (`ChunkMetadata`) applied to every chunk, containing exactly: `doc_id`, `title`, `regulator`, `circular_no`, `issue_date`, `effective_date`, `status`, `supersedes`, `section`, `page`, `access_level`, `source_url`, `content_hash`, and `chunk_index`.
- **Reasoning:** Regulatory queries are highly specific. By structuring these properties up front, we allow the vector database (Qdrant) to perform exact "pre-filtering" (e.g., `regulator == "RBI"` AND `issue_date == "2024-01-01"`) before running the semantic vector search. The metadata itself provides essential traceability back to the source document and regulatory context.
- **Trade-offs and Limitations:** Storing 14 fields on every chunk increases the payload size per point in the database. Furthermore, the pipeline is highly dependent on the upstream manifest or parser correctly providing this information; missing upstream data will result in `None` values that cannot be filtered. Note that metadata fields alone do not make ingestion idempotent; the pipeline relies separately on a PostgreSQL registry for file change detection and deterministic UUIDv5 Qdrant point IDs (derived from `doc_id` and `chunk_index`) to ensure safe re-runs.

---

## Decision 007: Frozen Retrieval Baseline and Failure Analysis (Phase 2, Step 2.6)

### Status
Accepted

### Context
The Step 2.5 dense-retrieval baseline is frozen before retrieval improvements. Twelve development questions were investigated against original PDFs and read-only indexed chunks; hold-out questions were excluded.

### Decisions Made

1. **Frozen baseline and comparison rule**
   - Source: [committed baseline JSON](eval/results/retrieval_20261012T191839173509Z_af6558ebe4a5bce1f853b19340b8acdfe77ea87db78f6dd033f4fb3c73a9c58f.json), timestamp `20261012T191839173509Z`.
   - Dense retrieval, `k=5`, embedding model `BAAI/bge-small-en-v1.5`, Qdrant collection `policylens_chunks`. Of 60 golden questions, 12 frozen hold-out questions were excluded; 48 development questions remained, with 41 answerable questions evaluated and 7 unanswerable questions excluded.
   - Configuration SHA-256: `af6558ebe4a5bce1f853b19340b8acdfe77ea87db78f6dd033f4fb3c73a9c58f`. Two saved runs have the same hash and identical full-precision aggregate metrics. This hash identifies recorded settings, **not** the Qdrant index snapshot or embedding artifacts.

   | Experiment/configuration | Hit@5 | Recall@5 | MRR | Notes |
   | --- | ---: | ---: | ---: | --- |
   | Baseline: dense BGE, `k=5`, `policylens_chunks` | 0.9268 | 0.8561 | 0.8862 | 41 answerable development questions; 12 hold-out excluded |

   Future retrieval experiments must use the same evaluation split and metric definitions for comparison. No improvement results have been recorded.

2. **Failure taxonomy and investigated cases**
   - Parsing/extraction: confirmed for G035. Chunking/context fragmentation: observed in G028 and G036; incomplete answer-bearing chunk coverage in G050 and G052. Embedding/ranking misses: observed as absent or lower-ranked gold pages, without proving an embedding-model defect. Exact-identifier miss: likely for G042. Ambiguous questions and wrong filters were **not established** as causes in these cases.

   | ID | Confirmed observation | Likely explanation or limit |
   | --- | --- | --- |
   | G003 | Complete miss; the Payments Banks page is indexed, while Commercial Banks and Small Finance Banks passages rank higher. | Related-regulation ranking competition (medium confidence). |
   | G035 | Complete miss; the Digital Accessibility PDF is visually readable but yields zero extracted text and zero indexed chunks. | Parsing/extraction failure (confirmed, high confidence). |
   | G042 | Complete miss; the sanctions table and exact `5080(E)` mapping are indexed but absent from top five. | Exact-identifier retrieval miss (medium confidence). |
   | G007 | Partial recall: page 8 retrieved; indexed page 9 missing. | Ranking/coverage issue (medium confidence). |
   | G008 | Partial recall: pages 2, 7, 8 retrieved; indexed pages 5, 6 missing. Duplicate page-8 chunks and page 14 occupy top-five positions. | Crowding confirmed; underlying ranking cause untested. |
   | G012 | Partial recall: ETF extension page retrieved; indexed original page missing. The extension itself states both dates. | Version/provenance ranking miss (medium confidence). |
   | G017 | Partial recall: answer-bearing AIFI page 2 retrieved; contextual page 1 missing. Near-identical RBI valuation amendments occupy other ranks. | Near-duplicate ranking competition (medium confidence). |
   | G028 | Partial recall: OTC novation page 1 retrieved; indexed page 2 missing. Issue date and applicability rule span the pages. | Context split confirmed; effect on ranking is untested. |
   | G036 | Partial recall: delisting page 3 retrieved; indexed page 2 missing. The bank-route sentence crosses the page boundary. | Context split confirmed; likely ranking issue (medium confidence). |
   | G021 | Hit@5 and Recall@5 succeed; the first gold page is rank 2, after the same circular's introduction. | Minor ranking weakness, not an established substantive miss. |
   | G050 | Page-level Hit@5 and Recall@5 succeed; the returned gold-page chunk has the 60-day rule, but the separately indexed 90-day rule is absent. | Chunk-level answer-evidence gap confirmed; ranking cause undetermined. |
   | G052 | Page-level Hit@5 and Recall@5 succeed; a related IFSCA circular ranks first, while returned gold-page chunks omit separately indexed LRS and overseas-labelling text. | Related-document competition and chunk-level evidence gap confirmed. |

   Page-level Hit@k and Recall@k can equal 1 even when returned chunks omit part of the required answer, as G050 and G052 show. Similarity scores alone do not establish relevance or a root cause.

3. **Future improvement hypotheses, not implemented**
   - Test extraction support for image-only/non-extractable PDFs; stronger exact-identifier matching; diversity against near-duplicate chunks; neighboring-chunk/page context for multi-section questions; and chunk-level answer-evidence coverage checks. These are untested hypotheses, not measured gains. No tuning was performed.
