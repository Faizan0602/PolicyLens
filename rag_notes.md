# PolicyLens — Phase 2 Step 2.2: Manual RAG Evaluation

## Test configuration

- Provider: GroqCloud
- Model: `qwen/qwen3.8-27b`
- Retrieval: Qdrant dense top-k through the LCEL RAG chain
- k: 5
- Queries: 10, manually executed

Results below record the observed manual outcomes.

## Results

| Query and topic | Result | Key observation | Supporting sources |
| --- | --- | --- | --- |
| Q1 — Note Sorting Machines | Correct | Answer judged correct. | Source 1, page 10; Source 2, page 1 |
| Q2 — NRD-CSR | Correct | Deadline: 10th of the following month. | Source 3, page 2 |
| Q3 — Form A2 | Correct | Approval by the Board or delegated committee. | Source 2, page 1 |
| Q4 — Payments Banks | Correct | Qualifying entities and promoter-group exclusion covered. | Source 5, page 2 |
| Q5 — Project Jagrook | Correct | Alternate-day app messages and risk disclosures. | Source 3, page 2 |
| Q6 — FIRE | Partially correct | Correct 6-hour email and 24-hour portal deadlines, but unsupported framework/PDF references added. | — |
| Q7 — ETF fallback NAV | Abstained | Answer-bearing chunk missed by top-5; expected latest available closing NAV. | — |
| Q8 — ETF extension | Correct | September 7 instead of September 1. | Sources 2 and 3, page 1 |
| Q9 — Digital Accessibility | Appropriately abstained | Relevant PDF produced zero indexed chunks. | — |
| Q10 — Repo rate | Appropriately abstained | No supporting corpus evidence. | — |

Source tags are local to each query; only observed supporting tags/pages are listed.

## Findings

- **6 correct answers:** Q1, Q2, Q3, Q4, Q5, and Q8.
- **1 partially correct answer:** Q6 had correct deadlines but unsupported additions.
  Correct core facts did not justify the additional framework/PDF references.
- **3 abstentions:** Q7, Q9, and Q10.
- **Q7 — retrieval miss:** An answer-bearing indexed chunk was missed by top-5 retrieval.
  The expected answer was the latest available closing NAV.
  Abstention avoided an unsupported answer but did not resolve the retrieval miss.
- **Q9 — coverage gap:** The Digital Accessibility PDF produced zero indexed chunks.
  Its evidence was unavailable to retrieval; the model appropriately abstained.
- **Q10 — corpus gap:** Insufficient corpus evidence supported abstention.
  No repo-rate figure should be inferred from unrelated text.
- **Source records represent retrieved evidence, not automatically validated citations.**
  A returned source record does not prove that each generated claim is supported.

## Limitations

- No automatic citation validation.
- No guaranteed hallucination prevention.
- No relevance filtering or reranking.
- No native token streaming; `generate()` waits for the complete response.
