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
