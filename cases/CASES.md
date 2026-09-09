# The four required cases

Generated from the live knowledge layer by `scripts/export_cases.py`. Nothing here is
hand-written or hard-coded: each case is the top-ranked example of its kind among the
relations the system actually produced, selected by `factlayer/cases.py`.

## Corpus

| document | pages | facts | primary entity |
|---|---:|---:|---|
| `03-delhivery-q4-fy24-earnings-presentation.pdf` | 27 | 118 | Delhivery Limited |
| `02-delhivery-annual-report-fy24-excerpt.pdf` | 100 | 968 | Delhivery Limited |
| `01-delhivery-prospectus-2022-excerpt.pdf` | 100 | 724 | Delhivery Corp Limited |
| `01-india-economic-survey-2024-25-excerpt.pdf` | 89 | 329 | India |
| `02-rbi-annual-report-2024-25-excerpt.pdf` | 100 | 622 | India |
| `03-imf-india-2025-article-iv-excerpt.pdf` | 95 | 371 | India |

| metric | value |
|---|---:|
| documents | 6 |
| facts | 3,132 |
| facts grounded | 2,856 |
| relations | 2,713 |
| relations cross doc | 611 |
| relations · CONTRADICTS | 10 |
| relations · CORROBORATES | 203 |
| relations · RECONCILED | 291 |
| relations · RELATED | 2,209 |
| quarantined | 77 |
| distinct metrics | 1,325 |
| distinct qualifiers | 107 |
| distinct entities | 671 |

---

## Case 1 — A fact corroborated across documents, expressed differently

Ranked by how *differently* the two sources state the same agreeing fact, so the examples shown are the ones that only match because of normalization.

### 1. CORROBORATES  ·  confidence 0.99  ·  cross-document  ·  decided by `deterministic`

**Fact A — Delhivery Limited · revenue from services**

- Value as printed: `₹81,415Mn`
- Normalized: `INR 8,141.50 crore`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 4

> ₹81,415Mn Revenue from services

**Fact B — Delhivery Limited · revenue for services**

- Value as printed: `8,142`
- Normalized: `INR 8,142.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Revenue for services (A) 1,860 2,194 2,076 (5.4%) 11.6%

**System reasoning.** INR 8,141.50 crore and INR 8,142.00 crore agree to within 0.01% for FY2024, inside the 0.05% tolerance implied by how precisely each figure is written.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `8.1415e+10` vs `8.142e+10` |
| relative difference | `0.0061%` |
| verdict on that | within rounding tolerance |
| rounding tolerance | `0.0500%` (from how precisely each figure is written) |
| ratio A/B | `0.999939` |

</details>

### 2. CORROBORATES  ·  confidence 0.99  ·  cross-document  ·  decided by `deterministic`

**Fact A — Delhivery Limited · revenue from services**

- Value as printed: `81,415`
- Normalized: `INR 8,141.50 crore`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 6

> Revenue from services* (₹ million) 72,236 FY23 70,536 FY22 81,415 FY24

**Fact B — Delhivery Limited · revenue for services**

- Value as printed: `8,142`
- Normalized: `INR 8,142.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Revenue for services (A) 1,860 2,194 2,076 (5.4%) 11.6%

**System reasoning.** INR 8,141.50 crore and INR 8,142.00 crore agree to within 0.01% for FY2024, inside the 0.05% tolerance implied by how precisely each figure is written.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `8.1415e+10` vs `8.142e+10` |
| relative difference | `0.0061%` |
| verdict on that | within rounding tolerance |
| rounding tolerance | `0.0500%` (from how precisely each figure is written) |
| ratio A/B | `0.999939` |

</details>

### 3. CORROBORATES  ·  confidence 0.99  ·  cross-document  ·  decided by `deterministic`

**Fact A — Delhivery Limited · revenue for services**

- Value as printed: `7,224`
- Normalized: `INR 7,224.00 crore`
- Period: `FY23` → `FY2023`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Revenue for services (A) 1,860 2,194 2,076 (5.4%) 11.6%

**Fact B — Delhivery Limited · revenue from services**

- Value as printed: `72,236`
- Normalized: `INR 7,223.60 crore`
- Period: `FY23` → `FY2023`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 6

> Revenue from services* (₹ million) 72,236 FY23

**System reasoning.** INR 7,224.00 crore and INR 7,223.60 crore agree to within 0.01% for FY2023, inside the 0.05% tolerance implied by how precisely each figure is written.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2023 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `7.224e+10` vs `7.2236e+10` |
| relative difference | `0.0055%` |
| verdict on that | within rounding tolerance |
| rounding tolerance | `0.0500%` (from how precisely each figure is written) |
| ratio A/B | `1.00006` |

</details>


---

## Case 2 — A genuine or likely contradiction

Same metric, same subject, same resolved period, and no stated difference in basis, scope or units — yet the figures disagree by more than rounding can explain.

### 1. CONTRADICTS  ·  confidence 0.90  ·  same document  ·  decided by `hybrid`  ·  explained by **definition**

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

### 2. CONTRADICTS  ·  confidence 0.65  ·  same document  ·  decided by `deterministic`

**Fact A — Global economy · growth rate**

- Value as printed: `3.5 per cent`
- Normalized: `3.50 %`
- Period: `2024` → `2024`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 7

> global growth at 3.3 per cent in 2024 (3.5 per cent a year ago)

**Fact B — Global economy · growth rate**

- Value as printed: `3.3 per cent`
- Normalized: `3.30 %`
- Period: `2024` → `2024`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 7

> global growth at 3.3 per cent in 2024

**System reasoning.** Both sources report this metric for 2024, with no stated difference in basis, scope or units, yet the figures differ by 5.7% (3.50 % vs 3.30 %).

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover 2024 |
| units | `%` ↔ `%` (comparable) |
| values compared | `3.5` vs `3.3` |
| relative difference | `5.7143%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `1.5152%` (from how precisely each figure is written) |
| ratio A/B | `1.06061` |

</details>

### 3. CONTRADICTS  ·  confidence 0.65  ·  same document  ·  decided by `deterministic`

**Fact A — Spoton · Active Customers**

- Value as printed: `5,533`
- Normalized: `5,533`
- Period: `period ended December 31, 2021` → `12M to 2021-12-31`
- Source: `01-delhivery-prospectus-2022-excerpt.pdf`, page 59

> In addition, Spoton offers PTL freight services to 5,533 Active Customers across industry verticals.

**Fact B — Spoton · number of active customers**

- Value as printed: `5,541`
- Normalized: `5,541`
- Period: `2021` → `2021`
- Source: `01-delhivery-prospectus-2022-excerpt.pdf`, page 45

> No. of Active Customers 5,234 5,541 (1) Includes permanent

**System reasoning.** Both sources report this metric for 12M to 2021-12-31, with no stated difference in basis, scope or units, yet the figures differ by 0.1% (5,533 vs 5,541).

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover 12M to 2021-12-31 |
| units | `count` ↔ `count` (comparable) |
| values compared | `5,533` vs `5,541` |
| relative difference | `0.1444%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.0500%` (from how precisely each figure is written) |
| ratio A/B | `0.998556` |

</details>


---

## Case 3 — An apparent contradiction explained by context

The numbers disagree, but a stated difference in period, basis, scope, unit or currency accounts for it. The dimension that resolves the conflict is named.

### 1. RECONCILED  ·  confidence 0.90  ·  cross-document  ·  decided by `hybrid`  ·  explained by **period**

**Fact A — Food inflation · inflation rate**

- Value as printed: `6.7 per cent`
- Normalized: `6.70 %`
- Period: `2024-25` → `FY2025`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 10

> food inflation remained elevated at 6.7 per cent in 2024-25

**Fact B — Food inflation · inflation rate**

- Value as printed: `8.4 per cent`
- Normalized: `8.40 %`
- Period: `FY25` → `FY2025`
- Qualifiers: `measure=CFPI`
- Source: `01-india-economic-survey-2024-25-excerpt.pdf`, page 28

> Food inflation, measured by the Consumer Food Price Index (CFPI), has increased from 7.5 per cent in FY24 to 8.4 per cent in FY25 (April-December)

**System reasoning.** Fact A reports the full fiscal year 2024-25, while Fact B reports only the April-December period of FY25. The difference in the time period covered explains why the inflation figures do not match. Supporting words: “Fact B: '8.4 per cent in FY25 (April-December)'”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2025 |
| units | `%` ↔ `%` (comparable) |
| values compared | `6.7` vs `8.4` |
| relative difference | `20.2381%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.7463%` (from how precisely each figure is written) |
| ratio A/B | `0.797619` |
| qualifier `measure` | A=`(unstated)` · B=`CFPI` |
| hypothesis 1 | stated measure differs (unstated vs CFPI), a definition difference |
| rule-based verdict | `RECONCILED` — confirmed by the adjudicator |

</details>

### 2. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `hybrid`  ·  explained by **period**

**Fact A — Delhivery Limited · EBITDA**

- Value as printed: `₹(452) Cr`
- Normalized: `INR -452.00 crore`
- Period: `FY23` → `FY2023`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 6

> FY23: ₹(452) Cr / (6.3%)

**Fact B — Delhivery Limited · EBITDA**

- Value as printed: `₹13 Cr`
- Normalized: `INR 13.00 crore`
- Period: `Q4 FY23` → `Q4 FY2023`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 7

> Q4 FY23: ₹13 Cr / 0.7%

**System reasoning.** Fact A represents the full fiscal year (FY23) EBITDA, while Fact B represents only the fourth quarter (Q4 FY23). The full-year loss of ₹452 Cr is consistent with a profitable fourth quarter of ₹13 Cr, implying significant losses in the preceding three quarters. Supporting words: “FY23: ₹(452) Cr / (6.3%) ... Q4 FY23: ₹13 Cr / 0.7%”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `CONTAINS` — FY2023 contains Q4 FY2023 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `-4.52e+09` vs `1.3e+08` |
| relative difference | `102.8761%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `3.8462%` (from how precisely each figure is written) |
| ratio A/B | `-34.7692` |
| hypothesis 1 | the shorter period reports INR 13.00 crore, which exceeds the INR -452.00 crore reported for the longer period containing it -- consistent only if other sub-periods were negative |
| hypothesis 2 | periods nest: FY2023 contains Q4 FY2023 |
| rule-based verdict | `RECONCILED` — confirmed by the adjudicator |

</details>

### 3. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `hybrid`  ·  explained by **period**

**Fact A — India · forex reserves increase**

- Value as printed: `USD 59.4 billion`
- Normalized: `USD 59.40 bn`
- Period: `FY25` → `FY2025`
- Source: `01-india-economic-survey-2024-25-excerpt.pdf`, page 71

> In H1 of FY25, forex reserves rose by USD 59.4 billion

**Fact B — India · forex reserves increase**

- Value as printed: `USD 27.1 billion`
- Normalized: `USD 27.10 bn`
- Period: `2024` → `2024`
- Source: `01-india-economic-survey-2024-25-excerpt.pdf`, page 71

> India’s forex reserves witnessed a notable increase of USD 27.1 billion in 2024.

**System reasoning.** The facts refer to different timeframes: Fact A covers the first half of the fiscal year 2025 (April to September 2024), while Fact B covers the calendar year 2024. Because the periods are not identical, the difference in values does not constitute a contradiction. Supporting words: “Fact A: "In H1 of FY25"; Fact B: "in 2024"”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `OVERLAPS` — FY2025 partially overlaps 2024 |
| units | `USD` ↔ `USD` (comparable) |
| values compared | `5.94e+10` vs `2.71e+10` |
| relative difference | `54.3771%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.1845%` (from how precisely each figure is written) |
| ratio A/B | `2.19188` |
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
| rule verdicts overturned | 1 |

### Why facts were rejected

| reason | count |
|---|---:|
| `table_association_unverifiable` | 57 |
| `evidence_too_short` | 20 |

### Where the adjudicator overturned the deterministic verdict

The most useful place to look for reasoning errors on either side.

### 1. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `llm`  ·  explained by **period**

**Fact A — Global economy · GDP growth**

- Value as printed: `3.5 per cent`
- Normalized: `3.50 %`
- Period: `2024` → `2024`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 22

> Global GDP grew by 3.3 per cent in 2024 (3.5 per cent a year ago)

**Fact B — Global economy · GDP growth**

- Value as printed: `3.3 per cent`
- Normalized: `3.30 %`
- Period: `2024` → `2024`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 22

> Global GDP grew by 3.3 per cent in 2024

**System reasoning.** Fact A reports 3.5% as the growth rate for 'a year ago' (2023), while Fact B correctly identifies 3.3% as the growth rate for 2024. The document text in Fact A clarifies that the 3.5% figure refers to the prior year, not 2024. Supporting words: “Fact A: "3.5 per cent a year ago"; Fact B: "Global GDP grew by 3.3 per cent in 2024"”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover 2024 |
| units | `%` ↔ `%` (comparable) |
| values compared | `3.5` vs `3.3` |
| relative difference | `5.7143%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `1.5152%` (from how precisely each figure is written) |
| ratio A/B | `1.06061` |
| rule-based verdict | `CONTRADICTS` — **overturned** by the adjudicator |

</details>

