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
| relations | 2,685 |
| relations cross doc | 598 |
| relations · CONTRADICTS | 10 |
| relations · CORROBORATES | 171 |
| relations · RECONCILED | 322 |
| relations · RELATED | 2,182 |
| quarantined | 180 |
| distinct metrics | 1,322 |
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

**Fact A — Delhivery Limited · revenue from services**

- Value as printed: `₹81,415Mn`
- Normalized: `INR 8,141.50 crore`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 4

> ₹81,415Mn Revenue from services

**Fact B — Delhivery Limited · revenue from services**

- Value as printed: `₹8,142 Cr`
- Normalized: `INR 8,142.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 6

> ₹8,142 Cr FY24 revenue from services

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


---

## Case 2 — A genuine or likely contradiction

Same metric, same subject, same resolved period, and no stated difference in basis, scope or units — yet the figures disagree by more than rounding can explain.

### 1. CONTRADICTS  ·  confidence 0.65  ·  same document  ·  decided by `deterministic`

**Fact A — Delhivery Limited · adjusted ebitda**

- Value as printed: `(2,532)`
- Normalized: `-2,532`
- Period: `FY21` → `FY2021`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 6

> Adjusted EBITDA (₹ million) and adjusted EBITDA margin (%)* FY20 FY21 FY22 FY23 FY24 Net working capital days 73 47 37 3

**Fact B — Delhivery Limited · adjusted ebitda**

- Value as printed: `(2,258)`
- Normalized: `-2,258`
- Period: `FY21` → `FY2021`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 7

> In FY22, when our express parcel volumes more than doubled and part truckload tonnage grew by around 40% on a pro forma basis, our adjusted EBITDA swung from negative ₹2,258 million in FY21 to positive ₹715 million on a pro forma basis.

**System reasoning.** Both sources report this metric for FY2021, with no stated difference in basis, scope or units, yet the figures differ by 10.8% (-2,532 vs -2,258).

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2021 |
| units | `count` ↔ `count` (comparable) |
| values compared | `-2,532` vs `-2,258` |
| relative difference | `10.8215%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.0500%` (from how precisely each figure is written) |
| ratio A/B | `1.12135` |

</details>

### 2. CONTRADICTS  ·  confidence 0.90  ·  same document  ·  decided by `llm`  ·  explained by **period**

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

**Fact A — Food inflation · inflation rate**

- Value as printed: `8.4 per cent`
- Normalized: `8.40 %`
- Period: `FY25` → `FY2025`
- Qualifiers: `measure=CFPI`
- Source: `01-india-economic-survey-2024-25-excerpt.pdf`, page 28

> Food inflation, measured by the Consumer Food Price Index (CFPI), has increased from 7.5 per cent in FY24 to 8.4 per cent in FY25 (April-December)

**Fact B — Food inflation · inflation rate**

- Value as printed: `2.9 per cent`
- Normalized: `2.90 %`
- Period: `March 2025` → `Mar 2025`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 10

> declining dramatically to 2.9 per cent by March 2025.

**System reasoning.** These are the same metric over nested periods: FY2025 contains Mar 2025. The difference is one of reporting window, not a disagreement.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `CONTAINS` — FY2025 contains Mar 2025 |
| units | `%` ↔ `%` (comparable) |
| values compared | `8.4` vs `2.9` |
| relative difference | `65.4762%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `1.7241%` (from how precisely each figure is written) |
| ratio A/B | `2.89655` |
| qualifier `measure` | A=`CFPI` · B=`(unstated)` |
| hypothesis 1 | periods nest: FY2025 contains Mar 2025 |
| hypothesis 2 | stated measure differs (CFPI vs unstated), a definition difference |

</details>

### 3. RECONCILED  ·  confidence 0.70  ·  cross-document  ·  decided by `deterministic`  ·  explained by **period**

**Fact A — India · current account deficit**

- Value as printed: `0.6 percent`
- Normalized: `0.60 %`
- Period: `FY2024/25` → `FY2025`
- Source: `03-imf-india-2025-article-iv-excerpt.pdf`, page 52

> The CA deficit declined to 0.6 percent of GDP in FY2024/25

**Fact B — India · current account deficit**

- Value as printed: `1.2 per cent`
- Normalized: `1.20 %`
- Period: `Q2 FY25` → `Q2 FY2025`
- Qualifiers: `measure=of GDP`
- Source: `01-india-economic-survey-2024-25-excerpt.pdf`, page 30

> India’s current account deficit (CAD) remains relatively contained at 1.2 per cent of GDP in Q2 FY25.

**System reasoning.** These are the same metric over nested periods: FY2025 contains Q2 FY2025. The difference is one of reporting window, not a disagreement.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `CONTAINS` — FY2025 contains Q2 FY2025 |
| units | `%` ↔ `%` (comparable) |
| values compared | `0.6` vs `1.2` |
| relative difference | `50.0000%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `8.3333%` (from how precisely each figure is written) |
| ratio A/B | `0.5` |
| qualifier `measure` | A=`(unstated)` · B=`of GDP` |
| hypothesis 1 | periods nest: FY2025 contains Q2 FY2025 |
| hypothesis 2 | stated measure differs (unstated vs of GDP), a definition difference |

</details>


---

## Case 4 — Extraction and reasoning failures

Measured, not estimated. Every proposed fact is checked against the real page text before
storage; failures are written to a quarantine table with a reason instead of being dropped.

| measure | value |
|---|---:|
| facts stored | 3112 |
| quarantined | 180 |
| ungrounded stored | 279 |
| fuzzy grounded | 510 |
| unresolved period | 647 |
| unresolved period pct | 20.8 |
| rule verdicts overturned | 1 |

### Why facts were rejected

| reason | count |
|---|---:|
| `table_association_unverifiable` | 155 |
| `evidence_too_short` | 24 |
| `value_present_but_quote_unverifiable` | 1 |

### Where the adjudicator overturned the deterministic verdict

The most useful place to look for reasoning errors on either side.

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

