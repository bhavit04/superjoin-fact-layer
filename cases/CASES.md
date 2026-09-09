# The four required cases

Generated from the live knowledge layer by `scripts/export_cases.py`. Nothing here is
hand-written or hard-coded: each case is the top-ranked example of its kind among the
relations the system actually produced, selected by `factlayer/cases.py`.

## Corpus

| document | pages | facts | primary entity |
|---|---:|---:|---|
| `01-delhivery-prospectus-2022-excerpt.pdf` | 100 | 724 | Delhivery Corp Limited |
| `02-delhivery-annual-report-fy24-excerpt.pdf` | 100 | 968 | Delhivery Limited |
| `03-delhivery-q4-fy24-earnings-presentation.pdf` | 27 | 118 | Delhivery Limited |
| `01-india-economic-survey-2024-25-excerpt.pdf` | 89 | 329 | India |
| `02-rbi-annual-report-2024-25-excerpt.pdf` | 100 | 622 | India |
| `03-imf-india-2025-article-iv-excerpt.pdf` | 95 | 371 | India |

| metric | value |
|---|---:|
| documents | 6 |
| facts | 3,132 |
| facts grounded | 2,856 |
| relations | 2,683 |
| relations cross doc | 542 |
| relations · CONTRADICTS | 7 |
| relations · CORROBORATES | 202 |
| relations · RECONCILED | 286 |
| relations · RELATED | 2,188 |
| quarantined | 77 |
| distinct metrics | 1,325 |
| distinct qualifiers | 107 |
| distinct entities | 671 |

---

## Case 1 — A fact corroborated across documents, expressed differently

Ranked by how *differently* the two sources state the same agreeing fact, so the examples shown are the ones that only match because of normalization.

### 1. CORROBORATES  ·  confidence 0.95  ·  cross-document  ·  decided by `llm`  ·  explained by **period**

**Fact A — Delhivery Limited · revenue for services**

- Value as printed: `8,142`
- Normalized: `INR 8,142.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Revenue for services (A) 1,860 2,194 2,076 (5.4%) 11.6%

**Fact B — Delhivery Limited · revenue from services**

- Value as printed: `81,415.38`
- Normalized: `INR 8,141.54 crore`
- Period: `2024` → `2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 85

> Revenue from services* 81,415.38 72,236.47

**System reasoning.** Both facts report Delhivery's revenue from services for FY24/2024 as approximately INR 8,142 crore. The minor difference of 0.0057% is due to rounding. Supporting words: “Fact A: "Revenue for services (A) 1,860 2,194 2,076"
Fact B: "Revenue from services* 81,415.38"”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `OVERLAPS` — FY2024 partially overlaps 2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `8.142e+10` vs `8.14154e+10` |
| relative difference | `0.0057%` |
| verdict on that | within rounding tolerance |
| rounding tolerance | `0.0500%` (from how precisely each figure is written) |
| ratio A/B | `1.00006` |
| rule-based verdict | `RECONCILED` — **overturned** by the adjudicator |

</details>

### 2. CORROBORATES  ·  confidence 0.95  ·  cross-document  ·  decided by `llm`  ·  explained by **period**

**Fact A — Delhivery Limited · revenue for services**

- Value as printed: `7,224`
- Normalized: `INR 7,224.00 crore`
- Period: `FY23` → `FY2023`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Revenue for services (A) 1,860 2,194 2,076 (5.4%) 11.6%

**Fact B — Delhivery Limited · revenue from services**

- Value as printed: `72,236.47`
- Normalized: `INR 7,223.65 crore`
- Period: `2023` → `2023`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 85

> Revenue from services* 81,415.38 72,236.47

**System reasoning.** Both facts report revenue from services for the 2023 fiscal period. Fact A reports INR 7,224 crore and Fact B reports INR 7,223.65 crore (72,236.47 million). The difference of less than 0.01% is due to rounding.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `OVERLAPS` — FY2023 partially overlaps 2023 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `7.224e+10` vs `7.22365e+10` |
| relative difference | `0.0049%` |
| verdict on that | within rounding tolerance |
| rounding tolerance | `0.0500%` (from how precisely each figure is written) |
| ratio A/B | `1.00005` |
| rule-based verdict | `RECONCILED` — **overturned** by the adjudicator |

</details>

### 3. CORROBORATES  ·  confidence 0.99  ·  cross-document  ·  decided by `deterministic`

**Fact A — Delhivery Limited · revenue for services**

- Value as printed: `8,142`
- Normalized: `INR 8,142.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Revenue for services (A) 1,860 2,194 2,076 (5.4%) 11.6%

**Fact B — Delhivery Limited · revenue from services**

- Value as printed: `81,415`
- Normalized: `INR 8,141.50 crore`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 6

> Revenue from services* (₹ million) 72,236 FY23 70,536 FY22 81,415 FY24

**System reasoning.** INR 8,142.00 crore and INR 8,141.50 crore agree to within 0.01% for FY2024, inside the 0.05% tolerance implied by how precisely each figure is written.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `8.142e+10` vs `8.1415e+10` |
| relative difference | `0.0061%` |
| verdict on that | within rounding tolerance |
| rounding tolerance | `0.0500%` (from how precisely each figure is written) |
| ratio A/B | `1.00006` |

</details>


---

## Case 2 — A genuine or likely contradiction

Same metric, same subject, same resolved period, and no stated difference in basis, scope or units — yet the figures disagree by more than rounding can explain.

### 1. CONTRADICTS  ·  confidence 0.90  ·  cross-document  ·  decided by `llm`  ·  explained by **value**

**Fact A — Delhivery Limited · Cross Border Services revenue**

- Value as printed: `776`
- Normalized: `INR 776.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 10

> FY22 FY23 FY24 TL revenue Cross Border Services revenue (3) (₹ Cr) (₹ Cr) Suppl

**Fact B — Delhivery Limited · revenues from cross-border services**

- Value as printed: `1,525.31`
- Normalized: `INR 152.53 crore`
- Period: `2024` → `2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 36

> Revenues from cross-border services 1,525.31 1.87% 2,957.68 4.09%

**System reasoning.** Both facts report revenue for the same entity and metric for the same fiscal year (FY24/2024). The values (776 crore vs 152.53 crore) differ by over 80%, which is too large to be explained by minor reporting differences or period misalignment. They represent conflicting data points for the same annual performance.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `OVERLAPS` — FY2024 partially overlaps 2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `7.76e+09` vs `1.52531e+09` |
| relative difference | `80.3439%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.0644%` (from how precisely each figure is written) |
| ratio A/B | `5.08749` |
| rule-based verdict | `RECONCILED` — **overturned** by the adjudicator |

</details>

### 2. CONTRADICTS  ·  confidence 0.90  ·  cross-document  ·  decided by `llm`  ·  explained by **value**

**Fact A — Delhivery Limited · Cross Border Services revenue**

- Value as printed: `776`
- Normalized: `INR 776.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 10

> FY22 FY23 FY24 TL revenue Cross Border Services revenue (3) (₹ Cr) (₹ Cr) Suppl

**Fact B — Delhivery Limited · revenue from cross border services**

- Value as printed: `1,525.31`
- Normalized: `INR 152.53 crore`
- Period: `2024` → `2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 85

> Revenue from Cross Border services 1,525.31 2,957.68

**System reasoning.** Both facts refer to the same metric for the same fiscal year (FY24/2024). The values (776 crore vs 152.53 crore) differ by a magnitude that cannot be explained by simple period or unit differences. The discrepancy is material and represents a direct conflict in reported financial data.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `OVERLAPS` — FY2024 partially overlaps 2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `7.76e+09` vs `1.52531e+09` |
| relative difference | `80.3439%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.0644%` (from how precisely each figure is written) |
| ratio A/B | `5.08749` |
| rule-based verdict | `RECONCILED` — **overturned** by the adjudicator |

</details>

### 3. CONTRADICTS  ·  confidence 0.90  ·  same document  ·  decided by `hybrid`  ·  explained by **definition**

**Fact A — Delhivery Limited · adjusted ebitda**

- Value as printed: `(2,532)`
- Normalized: `INR -253.20 crore`
- Period: `FY21` → `FY2021`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 6

> Adjusted EBITDA (₹ million) and adjusted EBITDA margin (%)* FY20 FY21 FY22 FY23 FY24 Net working capital days 73 47 37 3

**Fact B — Delhivery Limited · adjusted ebitda**

- Value as printed: `(2,258)`
- Normalized: `INR -225.80 crore`
- Period: `FY21` → `FY2021`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 7

> In FY22, when our express parcel volumes more than doubled and part truckload tonnage grew by around 40% on a pro forma basis, our adjusted EBITDA swung from negative ₹2,258 million in FY21 to positive ₹715 million on a pro forma basis.

**System reasoning.** Both facts report Adjusted EBITDA for Delhivery Limited for FY2021, but provide materially different figures (-2,532 million vs -2,258 million). As both appear in the same document, this represents an internal inconsistency in the reporting rather than a difference in scope or period.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2021 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `-2.532e+09` vs `-2.258e+09` |
| relative difference | `10.8215%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.0500%` (from how precisely each figure is written) |
| ratio A/B | `1.12135` |
| rule-based verdict | `CONTRADICTS` — confirmed by the adjudicator |

</details>


---

## Case 3 — An apparent contradiction explained by context

The numbers disagree, but a stated difference in period, basis, scope, unit or currency accounts for it. The dimension that resolves the conflict is named.

### 1. RECONCILED  ·  confidence 0.95  ·  cross-document  ·  decided by `hybrid`  ·  explained by **period**

**Fact A — Delhivery Limited · EBITDA**

- Value as printed: `(4,516.08)`
- Normalized: `INR -451.61 crore`
- Period: `2023` → `2023`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 36

> EBITDA 1,266.41 (4,516.08)

**Fact B — Delhivery Limited · EBITDA**

- Value as printed: `₹13 Cr`
- Normalized: `INR 13.00 crore`
- Period: `Q4 FY23` → `Q4 FY2023`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 7

> Q4 FY23: ₹13 Cr / 0.7%

**System reasoning.** Fact A reports a full-year EBITDA loss for 2023, while Fact B reports a positive EBITDA for the specific fourth quarter of that fiscal year. For a metric like EBITDA, it is common for a profitable quarter to be nested within a loss-making full year. Supporting words: “Fact A: "EBITDA 1,266.41 (4,516.08)" Fact B: "Q4 FY23: ₹13 Cr / 0.7%"”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `CONTAINS` — 2023 contains Q4 FY2023 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `-4.51608e+09` vs `1.3e+08` |
| relative difference | `102.8786%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `3.8462%` (from how precisely each figure is written) |
| ratio A/B | `-34.7391` |
| hypothesis 1 | the shorter period reports INR 13.00 crore, which exceeds the INR -451.61 crore reported for the longer period containing it -- consistent only if other sub-periods were negative |
| hypothesis 2 | periods nest: 2023 contains Q4 FY2023 |
| rule-based verdict | `RECONCILED` — confirmed by the adjudicator |

</details>

### 2. RECONCILED  ·  confidence 0.95  ·  cross-document  ·  decided by `hybrid`  ·  explained by **period**

**Fact A — Delhivery Limited · EBITDA**

- Value as printed: `(4,516.08)`
- Normalized: `INR -451.61 crore`
- Period: `2023` → `2023`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 36

> EBITDA 1,266.41 (4,516.08)

**Fact B — Delhivery Limited · EBITDA**

- Value as printed: `Rs. 127 Cr`
- Normalized: `INR 127.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 5

> FY24 EBITDA increased by Rs. 578 Cr to Rs. 127 Cr

**System reasoning.** Fact A reports EBITDA for 2023 (FY23), whereas Fact B reports EBITDA for FY24. The difference is explained by comparing two distinct financial periods. Supporting words: “"EBITDA 1,266.41 (4,516.08)" and "FY24 EBITDA increased by Rs. 578 Cr to Rs. 127 Cr"”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `OVERLAPS` — 2023 partially overlaps FY2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `-4.51608e+09` vs `1.27e+09` |
| relative difference | `128.1217%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.3937%` (from how precisely each figure is written) |
| ratio A/B | `-3.55597` |
| rule-based verdict | `RECONCILED` — confirmed by the adjudicator |

</details>

### 3. RECONCILED  ·  confidence 0.95  ·  cross-document  ·  decided by `hybrid`  ·  explained by **period**

**Fact A — Delhivery Limited · adjusted EBITDA**

- Value as printed: `76`
- Normalized: `INR 76.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 23

> Adjusted EBITDA 6 92 21 (404) 76

**Fact B — Delhivery Limited · adjusted EBITDA**

- Value as printed: `(4,038.66)`
- Normalized: `INR -403.87 crore`
- Period: `2023` → `2023`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 36

> Adjusted EBITDA1 757.86 (4,038.66)

**System reasoning.** Fact A reports Adjusted EBITDA for FY24 (INR 76 crore), while Fact B reports Adjusted EBITDA for FY23/2023 (INR -403.87 crore). The different reporting periods explain the numeric difference. Supporting words: “Fact A: "FY24", Fact B: "2023"”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `OVERLAPS` — FY2024 partially overlaps 2023 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `7.6e+08` vs `-4.03866e+09` |
| relative difference | `118.8181%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.6579%` (from how precisely each figure is written) |
| ratio A/B | `-0.188181` |
| rule-based verdict | `RECONCILED` — confirmed by the adjudicator |

</details>


---

## Case 4 — Extraction and reasoning failures

Measured, not estimated. Every proposed fact is checked against the real page text before
storage; failures are written to a quarantine table with a reason instead of being dropped.

| measure | value |
|---|---:|
| facts stored | 3132 |
| quarantined | 77 |
| ungrounded stored | 276 |
| fuzzy grounded | 530 |
| unresolved period | 634 |
| unresolved period pct | 20.2 |
| rule verdicts overturned | 5 |

### Why facts were rejected

| reason | count |
|---|---:|
| `table_association_unverifiable` | 57 |
| `evidence_too_short` | 20 |

### Where the adjudicator overturned the deterministic verdict

The most useful place to look for reasoning errors on either side.

### 1. RELATED  ·  confidence 1.00  ·  same document  ·  decided by `llm`  ·  explained by **identity**

**Fact A — Audit Committee · member**

- Value as printed: `Suvir Suren Sujan`
- Qualifiers: `role=Non-Executive Nominee Director`
- Source: `01-delhivery-prospectus-2022-excerpt.pdf`, page 92

> (c) Suvir Suren Sujan, Non-Executive Nominee Director (Member).

**Fact B — Audit Committee · member**

- Value as printed: `Srivatsan Rajan`
- Qualifiers: `role=Non-Executive Independent Director`
- Source: `01-delhivery-prospectus-2022-excerpt.pdf`, page 92

> (b) Srivatsan Rajan, Non-Executive Independent Director (Member); and

**System reasoning.** Fact A and Fact B identify different individuals serving as members of the same Audit Committee. They are not conflicting claims about the same person or role, but rather a list of distinct committee members.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `UNKNOWN` — at least one period could not be resolved |
| units | `` vs `` — **not directly comparable** |
| qualifier `role` | A=`Non-Executive Nominee Director` · B=`Non-Executive Independent Director` |
| rule-based verdict | `CONTRADICTS` — **overturned** by the adjudicator |

</details>

### 2. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `llm`  ·  explained by **definition**

**Fact A — Mr. Anindya Ghose · board role**

- Value as printed: `member of the Committee`
- Period: `2023` → `2023`
- Qualifiers: `committee=Risk Management Committee`, `effective_date=November 04, 2023`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 44

> Mr. Anindya Ghose has been appointed as member of the Committee with effect from November 04, 2023.

**Fact B — Mr. Anindya Ghose · board role**

- Value as printed: `Non-Executive Independent Director`
- Period: `2023` → `2023`
- Qualifiers: `effective_date=August 04, 2023`, `status=appointed`, `tenure=5 years`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 40

> Mr. Anindya Ghose was appointed as Non-Executive Independent Director for a period of 5 years with effect from August 04, 2023.

**System reasoning.** The facts describe different roles held by the same individual. Fact A refers to an appointment to a specific committee (Risk Management Committee), while Fact B refers to an appointment as a Non-Executive Independent Director. These are distinct board-related positions. Supporting words: “Fact A: "member of the Committee"; Fact B: "Non-Executive Independent Director"”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover 2023 |
| units | `` vs `` — **not directly comparable** |
| qualifier `committee` | A=`Risk Management Committee` · B=`(unstated)` |
| qualifier `effective_date` | A=`November 04, 2023` · B=`August 04, 2023` |
| qualifier `tenure` | A=`(unstated)` · B=`5 years` |
| qualifier `status` | A=`(unstated)` · B=`appointed` |
| hypothesis 1 | stated status differs (unstated vs appointed), a vintage difference |
| rule-based verdict | `CONTRADICTS` — **overturned** by the adjudicator |

</details>

