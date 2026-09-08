# The four required cases

Generated from the live knowledge layer by `scripts/export_cases.py`. Nothing here is
hand-written or hard-coded: each case is the top-ranked example of its kind among the
relations the system actually produced, selected by `factlayer/cases.py`.

## Corpus

| document | pages | facts | primary entity |
|---|---:|---:|---|
| `02-delhivery-annual-report-fy24-excerpt.pdf` | 100 | 964 | Delhivery Limited |
| `01-delhivery-prospectus-2022-excerpt.pdf` | 100 | 712 | Delhivery Corp Limited |
| `01-india-economic-survey-2024-25-excerpt.pdf` | 89 | 329 | India |
| `02-rbi-annual-report-2024-25-excerpt.pdf` | 100 | 622 | India |
| `03-imf-india-2025-article-iv-excerpt.pdf` | 95 | 367 | India |
| `03-delhivery-q4-fy24-earnings-presentation.pdf` | 27 | 118 | Delhivery Limited |

| metric | value |
|---|---:|
| documents | 6 |
| facts | 3,112 |
| facts grounded | 2,833 |
| relations | 2,783 |
| relations cross doc | 629 |
| relations · CONTRADICTS | 14 |
| relations · CORROBORATES | 187 |
| relations · RECONCILED | 364 |
| relations · RELATED | 2,218 |
| quarantined | 155 |
| distinct metrics | 1,322 |
| distinct qualifiers | 107 |
| distinct entities | 671 |

---

## Case 1 — A fact corroborated across documents, expressed differently

Ranked by how *differently* the two sources state the same agreeing fact, so the examples shown are the ones that only match because of normalization.

### 1. CORROBORATES  ·  confidence 0.99  ·  cross-document  ·  decided by `deterministic`

**Fact A — Delhivery Limited · revenue for services**

- Value as printed: `8,142`
- Normalized: `INR 8,142.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Revenue for services (A) 1,860 2,194 2,076 (5.4%) 11.6%

**Fact B — Delhivery Limited · revenue from services**

- Value as printed: `₹81,415Mn`
- Normalized: `INR 8,141.50 crore`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 4

> ₹81,415Mn Revenue from services

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

### 2. CORROBORATES  ·  confidence 0.99  ·  cross-document  ·  decided by `deterministic`

**Fact A — Delhivery Limited · EBITDA**

- Value as printed: `Rs. 127 Cr`
- Normalized: `INR 127.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 5

> FY24 EBITDA increased by Rs. 578 Cr to Rs. 127 Cr

**Fact B — Delhivery Limited · EBITDA**

- Value as printed: `₹1,266Mn`
- Normalized: `INR 126.60 crore`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 4

> ₹1,266Mn EBITDA

**System reasoning.** INR 127.00 crore and INR 126.60 crore agree to within 0.31% for FY2024, inside the 0.39% tolerance implied by how precisely each figure is written.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `1.27e+09` vs `1.266e+09` |
| relative difference | `0.3150%` |
| verdict on that | within rounding tolerance |
| rounding tolerance | `0.3937%` (from how precisely each figure is written) |
| ratio A/B | `1.00316` |

</details>

### 3. CORROBORATES  ·  confidence 0.99  ·  cross-document  ·  decided by `deterministic`

**Fact A — Delhivery Limited · EBITDA**

- Value as printed: `₹127Cr`
- Normalized: `INR 127.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 6

> ₹127Cr / 1.6% EBITDA / EBITDA margin

**Fact B — Delhivery Limited · EBITDA**

- Value as printed: `₹1,266Mn`
- Normalized: `INR 126.60 crore`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 4

> ₹1,266Mn EBITDA

**System reasoning.** INR 127.00 crore and INR 126.60 crore agree to within 0.31% for FY2024, inside the 0.39% tolerance implied by how precisely each figure is written.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `1.27e+09` vs `1.266e+09` |
| relative difference | `0.3150%` |
| verdict on that | within rounding tolerance |
| rounding tolerance | `0.3937%` (from how precisely each figure is written) |
| ratio A/B | `1.00316` |

</details>


---

## Case 2 — A genuine or likely contradiction

Same metric, same subject, same resolved period, and no stated difference in basis, scope or units — yet the figures disagree by more than rounding can explain.

### 1. CONTRADICTS  ·  confidence 0.90  ·  same document  ·  decided by `llm`  ·  explained by **period**

**Fact A — Delhivery Limited · PTL freight tonnage**

- Value as printed: `1,517`
- Normalized: `1,517 tonnes`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 9

> 1,705 1,157 1,517 FY22 FY23 FY24 PTL freight tonnage(2)

**Fact B — Delhivery Limited · PTL freight tonnage**

- Value as printed: `384K Tons`
- Normalized: `384,000 tonnes`
- Period: `Q4 FY24` → `Q4 FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 7

> 384K Tons PTL freight tonnage in Q4 FY24

**System reasoning.** While the periods are nested (FY24 contains Q4 FY24), the reported tonnage for the single quarter (384,000 tonnes) is mathematically impossible to reconcile with the total reported for the full fiscal year (1,517 tonnes). Freight tonnage cannot be negative, so the Q4 figure cannot exceed the annual total.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `CONTAINS` — FY2024 contains Q4 FY2024 |
| units | `tonnes` ↔ `tonnes` (comparable) |
| values compared | `1,517` vs `384,000` |
| relative difference | `99.6049%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.1302%` (from how precisely each figure is written) |
| ratio A/B | `0.00395052` |
| hypothesis 1 | the shorter period reports 384,000 tonnes, which exceeds the 1,517 tonnes reported for the longer period containing it -- consistent only if other sub-periods were negative |
| hypothesis 2 | periods nest: FY2024 contains Q4 FY2024 |
| rule-based verdict | `RECONCILED` — **overturned** by the adjudicator |

</details>

### 2. CONTRADICTS  ·  confidence 0.65  ·  same document  ·  decided by `deterministic`

**Fact A — WPI · inflation**

- Value as printed: `2.3 per cent`
- Normalized: `2.30 %`
- Period: `2024-25` → `FY2025`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 48

> Inflation measured by the wholesale price index (WPI) increased to 2.3 per cent during 2024-25

**Fact B — WPI primary articles · inflation**

- Value as printed: `5.1 per cent`
- Normalized: `5.10 %`
- Period: `2024-25` → `FY2025`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 48

> WPI inflation in primary articles (weight of 22.6 per cent in the WPI basket) increased to 5.1 per cent during 2024-25

**System reasoning.** Both sources report this metric for FY2025, with no stated difference in basis, scope or units, yet the figures differ by 54.9% (2.30 % vs 5.10 %).

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2025 |
| units | `%` ↔ `%` (comparable) |
| values compared | `2.3` vs `5.1` |
| relative difference | `54.9020%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `2.1739%` (from how precisely each figure is written) |
| ratio A/B | `0.45098` |

</details>

### 3. CONTRADICTS  ·  confidence 0.65  ·  same document  ·  decided by `deterministic`

**Fact A — FPIs · net inflows**

- Value as printed: `USD 10.6 billion`
- Normalized: `USD 10.60 bn`
- Period: `December 2024` → `Dec 2024`
- Source: `01-india-economic-survey-2024-25-excerpt.pdf`, page 68

> t FPI inflows97 into India slowed to USD 10.6 billion from April to December 2024 from USD 31.7 billi

**Fact B — FPIs · net inflows**

- Value as printed: `USD 3.1 billion`
- Normalized: `USD 3.10 bn`
- Period: `December 2024` → `Dec 2024`
- Source: `01-india-economic-survey-2024-25-excerpt.pdf`, page 68

> with net inflows amounting to USD 3.1 billion in December 2024.

**System reasoning.** Both sources report this metric for Dec 2024, with no stated difference in basis, scope or units, yet the figures differ by 70.8% (USD 10.60 bn vs USD 3.10 bn).

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover Dec 2024 |
| units | `USD` ↔ `USD` (comparable) |
| values compared | `1.06e+10` vs `3.1e+09` |
| relative difference | `70.7547%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `1.6129%` (from how precisely each figure is written) |
| ratio A/B | `3.41935` |

</details>


---

## Case 3 — An apparent contradiction explained by context

The numbers disagree, but a stated difference in period, basis, scope, unit or currency accounts for it. The dimension that resolves the conflict is named.

### 1. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `hybrid`  ·  explained by **period**

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

### 2. RECONCILED  ·  confidence 0.70  ·  cross-document  ·  decided by `deterministic`  ·  explained by **period**

**Fact A — Delhivery Limited · revenue from services**

- Value as printed: `₹2,076 Cr`
- Normalized: `INR 2,076.00 crore`
- Period: `Q4 FY24` → `Q4 FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 7

> ₹2,076 Cr Q4 FY24 revenue from services

**Fact B — Delhivery Limited · revenue from services**

- Value as printed: `₹81,415Mn`
- Normalized: `INR 8,141.50 crore`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 4

> ₹81,415Mn Revenue from services

**System reasoning.** These are the same metric over nested periods: Q4 FY2024 falls inside FY2024. The difference is one of reporting window, not a disagreement.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `CONTAINED_BY` — Q4 FY2024 falls inside FY2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `2.076e+10` vs `8.1415e+10` |
| relative difference | `74.5010%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.0500%` (from how precisely each figure is written) |
| ratio A/B | `0.25499` |
| hypothesis 1 | periods nest: Q4 FY2024 falls inside FY2024 |

</details>

### 3. RECONCILED  ·  confidence 0.70  ·  cross-document  ·  decided by `deterministic`  ·  explained by **period**

**Fact A — Delhivery Limited · revenue for services**

- Value as printed: `2,194`
- Normalized: `INR 2,194.00 crore`
- Period: `Q3 FY24` → `Q3 FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Revenue for services (A) 1,860 2,194 2,076 (5.4%) 11.6% 7,

**Fact B — Delhivery Limited · revenue from services**

- Value as printed: `₹81,415Mn`
- Normalized: `INR 8,141.50 crore`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 4

> ₹81,415Mn Revenue from services

**System reasoning.** These are the same metric over nested periods: Q3 FY2024 falls inside FY2024. The difference is one of reporting window, not a disagreement.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `CONTAINED_BY` — Q3 FY2024 falls inside FY2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `2.194e+10` vs `8.1415e+10` |
| relative difference | `73.0516%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.0500%` (from how precisely each figure is written) |
| ratio A/B | `0.269484` |
| hypothesis 1 | periods nest: Q3 FY2024 falls inside FY2024 |

</details>


---

## Case 4 — Extraction and reasoning failures

Measured, not estimated. Every proposed fact is checked against the real page text before
storage; failures are written to a quarantine table with a reason instead of being dropped.

| measure | value |
|---|---:|
| facts stored | 3112 |
| quarantined | 155 |
| ungrounded stored | 279 |
| fuzzy grounded | 510 |
| unresolved period | 634 |
| unresolved period pct | 20.4 |
| rule verdicts overturned | 4 |

### Why facts were rejected

| reason | count |
|---|---:|
| `table_association_unverifiable` | 130 |
| `evidence_too_short` | 24 |
| `value_present_but_quote_unverifiable` | 1 |

### Where the adjudicator overturned the deterministic verdict

The most useful place to look for reasoning errors on either side.

### 1. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `llm`  ·  explained by **period**

**Fact A — Global economy · growth rate**

- Value as printed: `3.3 per cent`
- Normalized: `3.30 %`
- Period: `2024` → `2024`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 7

> global growth at 3.3 per cent in 2024

**Fact B — Global economy · growth rate**

- Value as printed: `3.5 per cent`
- Normalized: `3.50 %`
- Period: `2024` → `2024`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 7

> global growth at 3.3 per cent in 2024 (3.5 per cent a year ago)

**System reasoning.** Fact A refers to the 2024 growth projection. Fact B clarifies that the 3.5 per cent figure refers to the growth rate from 'a year ago' (2023), not 2024. The document is consistent; the extraction for Fact B misattributed the prior-year figure to the current year. Supporting words: “3.5 per cent a year ago”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover 2024 |
| units | `%` ↔ `%` (comparable) |
| values compared | `3.3` vs `3.5` |
| relative difference | `5.7143%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `1.5152%` (from how precisely each figure is written) |
| ratio A/B | `0.942857` |
| rule-based verdict | `CONTRADICTS` — **overturned** by the adjudicator |

</details>

### 2. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `llm`  ·  explained by **period**

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

