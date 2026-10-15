# Step 2.1: Manual dense retrieval notes

Status: Completed. All 10 queries were manually executed against the existing Qdrant dense retriever using k=5. Results were evaluated by inspecting retrieved evidence, not similarity scores alone.

Use the existing collection with k=5 for the initial pass:

```powershell
python -m policylens.retrieval --query "By when should banks submit the monthly NRD-CSR R012 return on CIMS?" --k 5
```

Inspect the actual chunk text. A similarity score is not a relevance probability.
Do not infer success from a score threshold. Top-k chunks may share a document.

## Queries and reference evidence

1. **What happens to previous Note Sorting Machine circulars when RBI issues RBI/DCM/2026-27/473?**
   Reference: `473MDD1229693F0604B6D996B1DF75C81E466.PDF`, page 1.
2. **By when should banks submit the monthly NRD-CSR R012 return on CIMS?**
   Reference: `NT2800AE75657FD144B8ABC111ECF504BCC06.PDF`, page 2; RBI/2026-27/280.
3. **Under RBI/2026-27/279, who can approve internal guidelines for online or physical Form A2 submission?**
   Reference: `NT2796737482352AE4E488C0ECB304A05CDE1.PDF`, page 1.
4. **Who qualifies as a 'qualifying person' under the October 1, 2026 Payments Banks shareholding amendment?**
   Reference: `NT277F3970CD9E76046B0870FB310FEAC22D9.PDF`, page 2; RBI/2026-27/277.
   Inspect whether similarly worded circulars for other bank categories displace this evidence.
5. **Under Project Jagrook, what must stock brokers display on trading apps from November 1, 2026?**
   Reference: `1790852162769.pdf`, page 2. Distinguish trading apps from websites.
6. **What reporting deadlines does SEBI's August 24, 2026 FIRE-format circular state for cyber incidents?**
   Reference: `1787569463244.pdf`, page 2. Bilingual extraction and acronym case.
7. **Under SEBI's June 15, 2026 ETF circular, what base price is used if no trade occurs on T-1?**
   Reference: `1781524158363.pdf`, page 2, paragraph 4.2.
8. **According to SEBI's August 28, 2026 extension circular, when do the June 15 ETF provisions come into effect?**
   Reference: `1787914585756.pdf`, page 1. Distinguish extension from original timeline.
9. **What revised compliance timelines are specified in SEBI's July 31, 2026 Digital Accessibility circular?**
   Reference document: `1785493077212.pdf`. Pre-implementation inspection found empty extracted text
   and zero indexed chunks for this file. This is a known coverage-gap probe, not an observed query outcome.
10. **What RBI policy repo rate was announced on October 1, 2026?**
    Unsupported-query probe: manifest inspection found no dedicated monetary-policy document;
    a search of extracted local PDF text found no occurrence of "repo rate".
    Do not assume nearest returned chunks contain answer evidence.

## Observation template

Copy this block for each query and fill it only after running and inspecting the results.

- Query number and exact query:
- Run date:
- k:

| Rank | Returned score | Source file | Page | Evidence excerpt | Evidence judgment (relevant / partial / irrelevant) |
| --- | --- | --- | --- | --- | --- |

- Relevant evidence retrieved (yes / partial / no):
- Failure reason, if observed:
- Other observations:

Record fewer rows if fewer results are returned. Mark unavailable metadata explicitly.
Possible failure reasons to investigate include wrong bank category, original rather than amended
timeline, TOC-only evidence, or absent indexed content. These are prompts for inspection, not outcomes.


Query 1: What happens to previous Note Sorting Machine circulars when RBI issues RBI/DCM/2026-27/473?
k=5
Outcome: PASS — direct answer retrieved at Rank 2 (score 0.836035), source 473MDD1229693F0604B6D996B1DF75C81E466.PDF, page 1.
Top-1: FAIL — Rank 1 (score 0.850833) is a related older-circular listing, not the direct answer.
Top-3: PASS.
Top-5: PASS.
Observation: Semantic similarity ranked a related historical reference above the actual withdrawal provision.

Query 2: By when should banks submit the monthly NRD-CSR R012 return on CIMS?
k=5
Outcome: PASS — direct answer at Rank 3, score 0.812573, RBI/2026-27/280, source NT2800AE75657FD144B8ABC111ECF504BCC06.PDF, page 2, paragraph 5.
Top-1: FAIL (reporting migration, not the deadline).
Top-3: PASS.
Top-5: PASS.
Observation: Correct document occupied all five results, but the answer-bearing deadline appeared third.

Query 3: Under RBI/2026-27/279, who can approve internal guidelines for online or physical Form A2 submission?
k=5
Outcome: PASS — direct answer retrieved at Rank 1, score 0.739550, circular RBI/2026-27/279, source NT2796737482352AE4E488C0ECB304A05CDE1.PDF, page 1.
Top-1: PASS.
Top-3: PASS.
Top-5: PASS.
Observation: Rank 2 (score 0.739061) was unrelated despite an almost identical similarity score; ranks 2-5 were irrelevant to the question.

Query 4: Who qualifies as a 'qualifying person' under the October 1, 2026 Payments Banks shareholding amendment?
k=5
Outcome: PASS — direct answer at Rank 1, score 0.785700, Payments Banks circular RBI/2026-27/277, source NT277F3970CD9E76046B0870FB310FEAC22D9.PDF, page 2.
Top-1: PASS. Top-3: PASS. Top-5: PASS.
Observation: Similar provisions from Commercial Banks, Small Finance Banks, and Local Area Banks appeared in other results; dense retrieval does not enforce bank-category specificity.

Query 5: Under Project Jagrook, what must stock brokers display on trading apps from November 1, 2026?
k=5
Outcome: PASS — direct answer at Rank 3, score 0.759906, source 1790852162769.pdf, page 2, section 4.2(b).
Top-1: FAIL — combines November website requirement and October voluntary trading-app rule, rather than the November app requirement.
Top-3: PASS. Top-5: PASS.
Answer: Specified investor awareness messages and risk disclosures, displayed on alternate days on the trading-app landing page (where an app exists).
Additional observation: Chunk metadata labels section as '4.1 Websites of Stock Brokers' although the answer is in section 4.2(b).

Query 6: What reporting deadlines does SEBI's August 24, 2026 FIRE-format circular state for cyber incidents?
k=5
Outcome: PASS — direct answer at Rank 1, score 0.771436, source 1787569463244.pdf, page 2.
Top-1: PASS. Top-3: PASS. Top-5: PASS.
Evidence: Reporting via mkt_incidents@sebi.gov.in within 6 hours and through SEBI Incident Reporting Portal within 24 hours.
Observation: Extracted sentence fragments appear across separate chunks; Rank 5 was an unrelated ETF timeline.

Query 7: Under SEBI's June 15, 2026 ETF circular, what base price is used if no trade occurs on T-1?
k=5
Outcome: PASS — direct answer at Rank 3, score 0.776982, original June 15 ETF circular, source 1781524158363.pdf, page 2, paragraph 4.2.
Answer: Latest available closing NAV of the ETF if no trade occurs at all on T-1.
Top-1: FAIL — August 28 extension circular ranked first but does not contain the base-price fallback rule.
Top-3: PASS. Top-5: PASS.
Observation: Related extension documents can outrank the actual regulatory provision.

Query 8: According to SEBI's August 28, 2026 extension circular, when do the June 15 ETF provisions come into effect?
k=5
Outcome: PASS — direct answer at Rank 1, score 0.827000, source 1787914585756.pdf, page 1, paragraph 3.
Answer: The effective date was extended from September 1, 2026 to September 7, 2026.
Top-1: PASS. Top-3: PASS. Top-5: PASS.
Observation: Rank 2 contains only the original deadline, and other unrelated timeline regulations occur in Top-5.

Query 9: What revised compliance timelines are specified in SEBI's July 31, 2026 Digital Accessibility circular?
k=5
Outcome: FAIL — no relevant evidence retrieved in Top-5.
Expected source: 1785493077212.pdf, previously confirmed to have zero indexed chunks.
Top-1: FAIL. Top-3: FAIL. Top-5: FAIL.
Returned ranks/scores: 1 ETF extension 0.758229; 2 OBPP 0.746408; 3 PaRRVA extension 0.730524; 4 Project Jagrook 0.715374; 5 ETF extension 0.714324.
Failure reason: Document coverage gap (no extractable text/indexed chunks); dense search returned semantically nearby but unrelated timeline circulars.

Query 10: What RBI policy repo rate was announced on October 1, 2026?
k=5
Outcome: FAIL — no answer-bearing evidence in Top-5.
Top-1: FAIL. Top-3: FAIL. Top-5: FAIL.
Highest result: Rank 1, score 0.711499, source NOTI27401102026AA16BFEFF59341BF97FD2930B1A4A63C.PDF, page 18.
Returned results: Rank 1 currency-management circular withdrawals (0.711499); Rank 2 ATM cassette swaps (0.704964); Rank 3 Commercial Banks investment directions (0.702993); Rank 4 Payments Banks investment directions (0.701479); Rank 5 Local Area Banks investment directions (0.699667).
Failure reason: No retrieved passage supports a policy repo-rate announcement. The corpus appears not to contain the requested evidence. Do not infer a repo-rate figure.

# Step 3.1: Dense vs Sparse BM25 Retrieval Evaluation

Status: Completed. Objective: compare sparse BM25 with the frozen dense baseline on the same answerable development questions, without using the hold-out.

## Configuration

- Dense: `BAAI/bge-small-en-v1.5` in `policylens_chunks`.
- Sparse: `qdrant/bm25` in `policylens_bm25`, named vector `bm25` with IDF modifier.
- Both collections contain 669 chunks with identical point IDs and complete payloads; retrieval depth was `k=5`.
- Of 48 development questions, 41 answerable questions were evaluated and 7 unanswerable questions were excluded. The 12 frozen hold-out questions were excluded.

## Results

| Method | Hit@5 | Recall@5 | MRR |
| --- | ---: | ---: | ---: |
| Dense | 0.9268 | 0.8561 | 0.8862 |
| BM25 | 0.9512 | 0.9049 | 0.8943 |

By question type (each cell is Hit@5 / Recall@5 / MRR):

| Type (count) | Dense | BM25 |
| --- | --- | --- |
| Factoid (19) | 0.8947 / 0.8421 / 0.8333 | 0.8947 / 0.8684 / 0.7719 |
| Multi-section (10) | 1 / 0.9100 / 0.9500 | 1 / 0.9100 / 1 |
| Table lookup (7) | 0.8571 / 0.8571 / 0.8571 | 1 / 1 / 1 |
| Date/version (5) | 1 / 0.8000 / 1 | 1 / 0.9000 / 1 |

## Question-level comparison

Compare Recall@5 first and reciprocal rank when recall ties; report Hit@5 separately. BM25 won 7 questions, dense won 5, and 29 were exact ties. Example cells are Hit@5 / Recall@5 / reciprocal rank.

| ID | Favored method | Dense | BM25 |
| --- | --- | --- | --- |
| G042 | BM25 | 0 / 0 / 0 | 1 / 1 / 1 |
| G007 | BM25 | 1 / 0.5 / 1 | 1 / 1 / 1 |
| G028 | BM25 | 1 / 0.5 / 1 | 1 / 1 / 1 |
| G009 | Dense | 1 / 1 / 1 | 1 / 0.5 / 1 |
| G004 | Dense | 1 / 1 / 1 | 1 / 1 / 0.3333 |
| G034 | Dense | 1 / 1 / 1 | 1 / 1 / 0.3333 |

## Findings and limitations

BM25 scored higher overall on this development set, while dense had higher factoid MRR. G003 and G035 were missed by both methods; G035 has a known extraction/indexing gap with zero indexed chunks. Page-level matches do not guarantee answer-bearing chunk text, raw dense and BM25 scores are not directly comparable, and metric differences alone do not establish causes. These results do not establish independent generalization. Future ingestion must keep both collections synchronized.

Saved evidence: [dense baseline](eval/results/retrieval_20261012T191839173509Z_af6558ebe4a5bce1f853b19340b8acdfe77ea87db78f6dd033f4fb3c73a9c58f.json), [BM25 evaluation](eval/results/retrieval_bm25_20261014T095834356877Z_5047cbf0cbf3f1ac63547757db03dfa232d1159d1d06350c5abca79b22162fe8.json). Associated architecture record: [Decision 008](DECISIONS.md#decision-008-separate-bm25-retrieval-and-development-set-comparison-phase-3-step-31).

# Step 3.2: Hybrid Search with Reciprocal Rank Fusion

Status: Completed for the fixed configuration below. The same 41 answerable development questions were evaluated; 7 unanswerable development questions and all 12 frozen hold-out questions were excluded.

## Architecture

- Manual RRF is implemented in `src/policylens/rrf.py`. Native Qdrant RRF uses the separate `policylens_hybrid` collection, leaving the dense and BM25 baseline collections unchanged.
- The hybrid collection has 669 points with verified matching IDs, complete payloads, and stored dense vectors. Its named vectors are `dense` and `bm25` (IDF).
- Each branch supplies five candidates; the fused result contains at most five. Manual smoothing is 60, corresponding to native `Rrf(k=61)` under the verified rank conventions.
- Manual and native RRF returned the same top-five point IDs in the same order for G042. This does not establish universal tie-order equivalence; G021 showed rank variation on equal RRF scores.

## Development-set ablation

| Method | Hit@5 | Recall@5 | MRR |
| --- | ---: | ---: | ---: |
| Dense | 0.9268 | 0.8561 | 0.8862 |
| BM25 | 0.9512 | 0.9049 | 0.8943 |
| Hybrid RRF | 0.9512 | 0.8927 | 0.8476 |

Hybrid results by question type (Hit@5 / Recall@5 / MRR):

| Type (count) | Hybrid |
| --- | --- |
| Factoid (19) | 0.8947 / 0.8421 / 0.7237 |
| Multi-section (10) | 1 / 0.9100 / 0.9500 |
| Table lookup (7) | 1 / 1 / 0.9286 |
| Date/version (5) | 1 / 0.9000 / 1 |

Against BM25, hybrid had one metric win (G004), six regressions (G008, G021, G034, G036, G042, G050), and 34 ties on Recall@5 and reciprocal rank. Hit@5 did not change for any of the 41 questions. G036 lost one gold page from the final five. G008 kept Recall@5 at 0.6 but returned gold pages 2, 7, and 8 instead of BM25's 2, 6, and 8.

## Candidate-level findings

- G042: A non-gold point ranked first in dense and third in BM25; contributions from both lists put it above the gold pages, which remained at fused ranks 2 and 4.
- G008: A non-gold page-14 point ranked second in both lists and became fused rank 1.
- G036: Gold page 2 was BM25 candidate rank 4 but fell outside the fused top five.
- G050: A non-gold page-5 point outranked gold page 4; both came from the same document.
- G021: The gold page and a non-gold page tied on RRF score. Repeated unchanged native queries placed the gold point at rank 1 or 2, explaining the saved reciprocal-rank regression without a candidate miss.
- G034: The gold point appeared in both candidate lists but ranked fourth after fusion. It ranked third in the separate BM25 collection and fourth in the hybrid collection's BM25 search, despite matching stored sparse vectors for the compared points and IDF in both collections; the reason for this small rank difference remains unverified.

These are development-set findings, not independent generalization. Page-level matches do not guarantee answer-bearing chunk text, and native tie ordering need not match the manual implementation. No parameter tuning was performed. BM25-only remains the best observed configuration here by Recall@5 and MRR, with Hit@5 tied with hybrid. Future ingestion must synchronize all three collections.

Saved evidence: [dense baseline](eval/results/retrieval_20261012T191839173509Z_af6558ebe4a5bce1f853b19340b8acdfe77ea87db78f6dd033f4fb3c73a9c58f.json), [BM25 evaluation](eval/results/retrieval_bm25_20261014T095834356877Z_5047cbf0cbf3f1ac63547757db03dfa232d1159d1d06350c5abca79b22162fe8.json), [hybrid evaluation](eval/results/retrieval_hybrid_20261014T112307814856Z_d0bfed4a543cfd45b7657595060f953681e1ee0360400368f28007db81c1c702.json).
