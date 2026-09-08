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
| relations · CONTRADICTS | 26 |
| relations · CORROBORATES | 248 |
| relations · RECONCILED | 451 |
| relations · RELATED | 2,058 |
| quarantined | 130 |
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

**Fact A — Delhivery Limited · EBITDA**

- Value as printed: `₹1,266Mn`
- Normalized: `INR 126.60 crore`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 4

> ₹1,266Mn EBITDA

**Fact B — Delhivery Limited · EBITDA**

- Value as printed: `₹127Cr`
- Normalized: `INR 127.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 6

> ₹127Cr / 1.6% EBITDA / EBITDA margin

**System reasoning.** INR 126.60 crore and INR 127.00 crore agree to within 0.31% for FY2024, inside the 0.39% tolerance implied by how precisely each figure is written.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `1.266e+09` vs `1.27e+09` |
| relative difference | `0.3150%` |
| verdict on that | within rounding tolerance |
| rounding tolerance | `0.3937%` (from how precisely each figure is written) |
| ratio A/B | `0.99685` |

</details>


---

## Case 2 — A genuine or likely contradiction

Same metric, same subject, same resolved period, and no stated difference in basis, scope or units — yet the figures disagree by more than rounding can explain.

### 1. CONTRADICTS  ·  confidence 0.90  ·  same document  ·  decided by `llm`  ·  explained by **unit**

**Fact A — Delhivery Limited · PTL freight tonnage**

- Value as printed: `1.4 Mn Tons`
- Normalized: `1.40 mn tonnes`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 6

> 1.4 Mn Tons PTL freight tonnage in FY24

**Fact B — Delhivery Limited · PTL freight tonnage**

- Value as printed: `1,517`
- Normalized: `1,517 tonnes`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 9

> 1,705 1,157 1,517 FY22 FY23 FY24 PTL freight tonnage(2)

**System reasoning.** While the mechanical observation suggests a scale mismatch, the values (1.4 million vs 1,517) are too far apart to be a simple unit conversion error (e.g., tons vs kg). Fact A claims 1.4 million tons, while Fact B claims 1,517 tons for the same metric and period in the same document, representing a material, unexplained discrepancy.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2024 |
| units | `tonnes` ↔ `tonnes` (comparable) |
| values compared | `1.4e+06` vs `1,517` |
| relative difference | `99.8916%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `3.5714%` (from how precisely each figure is written) |
| ratio A/B | `922.874` |
| hypothesis 1 | values differ by approximately a factor of 10^3, suggesting a scale or unit mismatch, suggesting a unit or scale mismatch |
| rule-based verdict | `RECONCILED` — **overturned** by the adjudicator |

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

### 2. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `hybrid`  ·  explained by **period**

**Fact A — Delhivery Limited · profit / (loss) after tax**

- Value as printed: `(1,008)`
- Normalized: `INR -1,008.00 crore`
- Period: `FY23` → `FY2023`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Profit / (Loss) after tax (159) 12 (69) (1,008) (249) EBIT

**Fact B — Delhivery Limited · profit / (loss) after tax**

- Value as printed: `(159)`
- Normalized: `INR -159.00 crore`
- Period: `Q4 FY23` → `Q4 FY2023`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Profit / (Loss) after tax (159) 12 (69) (1,008) (249) EBITD

**System reasoning.** Fact A reports the profit/loss for the full fiscal year (FY2023), while Fact B reports the figure for the fourth quarter (Q4 FY2023) of that same year. Because these represent different time periods, the figures are not expected to match. Supporting words: “Fact A: "FY23"; Fact B: "Q4 FY23"”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `CONTAINS` — FY2023 contains Q4 FY2023 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `-1.008e+10` vs `-1.59e+09` |
| relative difference | `84.2262%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.3145%` (from how precisely each figure is written) |
| ratio A/B | `6.33962` |
| hypothesis 1 | the shorter period reports INR -159.00 crore, which exceeds the INR -1,008.00 crore reported for the longer period containing it -- consistent only if other sub-periods were negative |
| hypothesis 2 | periods nest: FY2023 contains Q4 FY2023 |
| rule-based verdict | `RECONCILED` — confirmed by the adjudicator |

</details>

### 3. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `hybrid`  ·  explained by **period**

**Fact A — Delhivery Limited · profit / (loss) after tax**

- Value as printed: `12`
- Normalized: `INR 12.00 crore`
- Period: `Q3 FY24` → `Q3 FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Profit / (Loss) after tax (159) 12 (69) (1,008) (249) EB

**Fact B — Delhivery Limited · profit / (loss) after tax**

- Value as printed: `(249)`
- Normalized: `INR -249.00 crore`
- Period: `FY24` → `FY2024`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 17

> Profit / (Loss) after tax (159) 12 (69) (1,008) (249) EB

**System reasoning.** Fact A reports profit for a single quarter (Q3 FY2024), while Fact B reports the cumulative profit for the full fiscal year (FY2024). A positive quarterly result is mathematically consistent with a negative annual result if other quarters in the fiscal year incurred significant losses. Supporting words: “Profit / (Loss) after tax (159) 12 (69) (1,008) (249) EB”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `CONTAINED_BY` — Q3 FY2024 falls inside FY2024 |
| units | `INR` ↔ `INR` (comparable) |
| values compared | `1.2e+08` vs `-2.49e+09` |
| relative difference | `104.8193%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `4.1667%` (from how precisely each figure is written) |
| ratio A/B | `-0.0481928` |
| hypothesis 1 | the shorter period reports INR 12.00 crore, which exceeds the INR -249.00 crore reported for the longer period containing it -- consistent only if other sub-periods were negative |
| hypothesis 2 | periods nest: Q3 FY2024 falls inside FY2024 |
| rule-based verdict | `RECONCILED` — confirmed by the adjudicator |

</details>


---

## Case 4 — Extraction and reasoning failures

Measured, not estimated. Every proposed fact is checked against the real page text before
storage; failures are written to a quarantine table with a reason instead of being dropped.

| measure | value |
|---|---:|
| facts stored | 3112 |
| quarantined | 130 |
| ungrounded stored | 279 |
| fuzzy grounded | 510 |
| unresolved period | 634 |
| unresolved period pct | 20.4 |
| rule verdicts overturned | 5 |

### Why facts were rejected

| reason | count |
|---|---:|
| `table_association_unverifiable` | 105 |
| `evidence_too_short` | 24 |
| `value_present_but_quote_unverifiable` | 1 |

### Where the adjudicator overturned the deterministic verdict

The most useful place to look for reasoning errors on either side.

### 1. CORROBORATES  ·  confidence 1.00  ·  same document  ·  decided by `llm`

**Fact A — SVF Doorbell (Cayman) Ltd · board nomination rights**

- Value as printed: `one director`
- Qualifiers: `condition=for as long as SVF Doorbell (Cayman) Ltd and/or its affiliates continue to hold at least 10% of our Company’s issued and outstanding paid-up share capital on a fully diluted basis`, `effective_date=upon the commencement of listing and trading of our Company’s Equity Shares on the Stock Exchanges`, `status=conditional`
- Source: `01-delhivery-prospectus-2022-excerpt.pdf`, page 13

> SVF Doorbell (Cayman) Ltd shall be entitled to nominate one director on the Board, who shall be deemed to be a non-independent director for the purposes of our Company’s Board, for as long as SVF Doorbell (Cayman) Ltd and/or its affiliates continue to hold at least 10% of our Company’s issued and outstanding paid-up share capital on a fully diluted basis.

**Fact B — SVF Doorbell (Cayman) Ltd · board nomination right**

- Value as printed: `one non-executive, non-independent director`
- Qualifiers: `condition=SVF Doorbell (Cayman) Ltd and/or its affiliates continue to hold at least 10% of our Company’s issued and outstanding paid-up share capital on a fully diluted basis`
- Source: `01-delhivery-prospectus-2022-excerpt.pdf`, page 78

> SVF Doorbell (Cayman) Ltd shall be entitled to nominate one director on the Board, who shall be deemed to be a non-independent director for the purposes of our Company’s Board, for as long as SVF Doorbell (Cayman) Ltd and/or its affiliates continue to hold at least 10% of our Company’s issued and outstanding paid-up share capital on a fully diluted basis.

**System reasoning.** Both facts describe the exact same board nomination right for SVF Doorbell (Cayman) Ltd, supported by identical source evidence. The minor difference in descriptive wording (Fact B adding 'non-executive') and the inclusion of metadata qualifiers in Fact A do not constitute a conflict.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `UNKNOWN` — at least one period could not be resolved |
| units | `` vs `` — **not directly comparable** |
| qualifier `effective_date` | A=`upon the commencement of listing and trading of our Company’s Equity Shares on the Stock Exchanges` · B=`(unstated)` |
| qualifier `condition` | A=`for as long as SVF Doorbell (Cayman) Ltd and/or its affiliates continue to hold at least 10% of our Company’s issued and outstanding paid-up share capital on a fully diluted basis` · B=`SVF Doorbell (Cayman) Ltd and/or its affiliates continue to hold at least 10% of our Company’s issued and outstanding paid-up share capital on a fully diluted basis` |
| qualifier `status` | A=`conditional` · B=`(unstated)` |
| hypothesis 1 | stated status differs (conditional vs unstated), a vintage difference |
| rule-based verdict | `CONTRADICTS` — **overturned** by the adjudicator |

</details>

### 2. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `llm`  ·  explained by **period**

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

