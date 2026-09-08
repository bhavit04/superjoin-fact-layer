# The four required cases

Generated from the live knowledge layer by `scripts/export_cases.py`. Nothing here is
hand-written or hard-coded: each case is the top-ranked example of its kind among the
relations the system actually produced, selected by `factlayer/cases.py`.

## Corpus

| document | pages | facts | primary entity |
|---|---:|---:|---|
| `03-delhivery-q4-fy24-earnings-presentation.pdf` | 27 | 118 | Delhivery Limited |
| `02-delhivery-annual-report-fy24-excerpt.pdf` | 100 | 964 | Delhivery Limited |
| `01-delhivery-prospectus-2022-excerpt.pdf` | 100 | 712 | Delhivery Corp Limited |
| `01-india-economic-survey-2024-25-excerpt.pdf` | 89 | 329 | India |
| `02-rbi-annual-report-2024-25-excerpt.pdf` | 100 | 622 | India |
| `03-imf-india-2025-article-iv-excerpt.pdf` | 95 | 367 | India |

| metric | value |
|---|---:|
| documents | 6 |
| facts | 3,112 |
| facts grounded | 2,833 |
| relations | 2,783 |
| relations cross doc | 634 |
| relations · CONTRADICTS | 44 |
| relations · CORROBORATES | 283 |
| relations · RECONCILED | 417 |
| relations · RELATED | 2,039 |
| quarantined | 97 |
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

### 1. CONTRADICTS  ·  confidence 1.00  ·  same document  ·  decided by `hybrid`  ·  explained by **definition**

**Fact A — Oils and fats · weight in cpi-food and beverages**

- Value as printed: `7.8 per cent`
- Normalized: `7.80 %`
- Period: `2024-25` → `FY2025`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 44

> Prices of oils and fats (weight of 7.8 per cent in CPI-food and beverages)

**Fact B — Oils and Fats · weight in cpi-food and beverages**

- Value as printed: `3.6`
- Normalized: `3.60 %`
- Period: `2024-25` → `FY2025`
- Source: `02-rbi-annual-report-2024-25-excerpt.pdf`, page 41

> Oils and Fats 3.6

**System reasoning.** Both facts claim to represent the weight of 'Oils and Fats' within the 'CPI-food and beverages' index for the same period (FY2025). Because they provide significantly different values (7.8% vs 3.6%) for the exact same metric and scope within the same document, they are in direct conflict.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2025 |
| units | `%` ↔ `%` (comparable) |
| values compared | `7.8` vs `3.6` |
| relative difference | `53.8462%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `1.3889%` (from how precisely each figure is written) |
| ratio A/B | `2.16667` |
| rule-based verdict | `CONTRADICTS` — confirmed by the adjudicator |

</details>

### 2. CONTRADICTS  ·  confidence 0.90  ·  same document  ·  decided by `llm`  ·  explained by **unit**

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

### 3. CONTRADICTS  ·  confidence 0.95  ·  same document  ·  decided by `hybrid`  ·  explained by **value**

**Fact A — India · net FDI**

- Value as printed: `USD 10.1 billion`
- Normalized: `USD 10.10 bn`
- Period: `FY24` → `FY2024`
- Source: `01-india-economic-survey-2024-25-excerpt.pdf`, page 66

> For FY24 as a whole, the net FDI was USD 10.1 billion.

**Fact B — India · net FDI**

- Value as printed: `USD 8.5 billion`
- Normalized: `USD 8.50 bn`
- Period: `FY24` → `FY2024`
- Source: `01-india-economic-survey-2024-25-excerpt.pdf`, page 66

> compared to USD 8.5 billion in the corresponding period of FY24.

**System reasoning.** Both facts refer to the same metric (net FDI) for the same period (FY24) within the same document. Fact A states the total was USD 10.1 billion, while Fact B claims it was USD 8.5 billion. The 15.8% difference is material and cannot be reconciled by the provided text.

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2024 |
| units | `USD` ↔ `USD` (comparable) |
| values compared | `1.01e+10` vs `8.5e+09` |
| relative difference | `15.8416%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.5882%` (from how precisely each figure is written) |
| ratio A/B | `1.18824` |
| rule-based verdict | `CONTRADICTS` — confirmed by the adjudicator |

</details>


---

## Case 3 — An apparent contradiction explained by context

The numbers disagree, but a stated difference in period, basis, scope, unit or currency accounts for it. The dimension that resolves the conflict is named.

### 1. RECONCILED  ·  confidence 0.95  ·  cross-document  ·  decided by `llm`  ·  explained by **period**

**Fact A — India · current account deficit**

- Value as printed: `0.6 percent`
- Normalized: `0.60 %`
- Period: `FY2024/25` → `FY2025`
- Source: `03-imf-india-2025-article-iv-excerpt.pdf`, page 52

> The CA deficit declined to 0.6 percent of GDP in FY2024/25

**Fact B — India · current account deficit**

- Value as printed: `1.2 per cent`
- Normalized: `1.20 %`
- Period: `FY25` → `FY2025`
- Source: `01-india-economic-survey-2024-25-excerpt.pdf`, page 62

> India’s current account deficit (CAD) moderated slightly to 1.2 per cent of GDP in Q2 of FY25

**System reasoning.** Fact A reports the current account deficit for the full fiscal year (FY2024/25), while Fact B specifically reports the deficit for the second quarter (Q2) of that same fiscal year. Supporting words: “Fact A: "The CA deficit declined to 0.6 percent of GDP in FY2024/25" vs Fact B: "current account deficit (CAD) moderated slightly to 1.2 per cent of GDP in Q2 of FY25"”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2025 |
| units | `%` ↔ `%` (comparable) |
| values compared | `0.6` vs `1.2` |
| relative difference | `50.0000%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `8.3333%` (from how precisely each figure is written) |
| ratio A/B | `0.5` |
| rule-based verdict | `CONTRADICTS` — **overturned** by the adjudicator |

</details>

### 2. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `hybrid`  ·  explained by **basis**

**Fact A — Delhivery Limited · revenue from services growth**

- Value as printed: `(5.4%)`
- Normalized: `-5.40 %`
- Period: `Q4 FY24` → `Q4 FY2024`
- Qualifiers: `basis=QoQ`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 7

> YoY: 11.6% / QoQ: (5.4%) (2)

**Fact B — Delhivery Limited · revenue from services growth**

- Value as printed: `11.6%`
- Normalized: `11.60 %`
- Period: `Q4 FY24` → `Q4 FY2024`
- Qualifiers: `basis=YoY`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 7

> YoY: 11.6% / QoQ: (5.4%) (2)

**System reasoning.** The two figures represent the same metric for the same period but use different comparison bases: Fact A is a Quarter-on-Quarter (QoQ) decline, while Fact B is a Year-on-Year (YoY) increase. Supporting words: “YoY: 11.6% / QoQ: (5.4%)”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover Q4 FY2024 |
| units | `%` ↔ `%` (comparable) |
| values compared | `-5.4` vs `11.6` |
| relative difference | `146.5517%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.9259%` (from how precisely each figure is written) |
| ratio A/B | `-0.465517` |
| qualifier `basis` | A=`QoQ` · B=`YoY` |
| hypothesis 1 | stated basis differs (QoQ vs YoY), a basis difference |
| rule-based verdict | `RECONCILED` — confirmed by the adjudicator |

</details>

### 3. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `hybrid`  ·  explained by **basis**

**Fact A — Delhivery Limited · Express parcel shipments growth**

- Value as printed: `(12.8%)`
- Normalized: `-12.80 %`
- Period: `Q4 FY24` → `Q4 FY2024`
- Qualifiers: `basis=QoQ`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 7

> YoY: (2.2%) / QoQ: (12.8%)

**Fact B — Delhivery Limited · Express parcel shipments growth**

- Value as printed: `(2.2%)`
- Normalized: `-2.20 %`
- Period: `Q4 FY24` → `Q4 FY2024`
- Qualifiers: `basis=YoY`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 7

> YoY: (2.2%) / QoQ: (12.8%)

**System reasoning.** The two facts report the same metric for the same period but use different comparison bases: Fact A reports a Quarter-on-Quarter (QoQ) decline, while Fact B reports a Year-on-Year (YoY) decline. Supporting words: “YoY: (2.2%) / QoQ: (12.8%)”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover Q4 FY2024 |
| units | `%` ↔ `%` (comparable) |
| values compared | `-12.8` vs `-2.2` |
| relative difference | `82.8125%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `2.2727%` (from how precisely each figure is written) |
| ratio A/B | `5.81818` |
| qualifier `basis` | A=`QoQ` · B=`YoY` |
| hypothesis 1 | stated basis differs (QoQ vs YoY), a basis difference |
| rule-based verdict | `RECONCILED` — confirmed by the adjudicator |

</details>


---

## Case 4 — Extraction and reasoning failures

Measured, not estimated. Every proposed fact is checked against the real page text before
storage; failures are written to a quarantine table with a reason instead of being dropped.

| measure | value |
|---|---:|
| facts stored | 3112 |
| quarantined | 97 |
| ungrounded stored | 279 |
| fuzzy grounded | 510 |
| unresolved period | 634 |
| unresolved period pct | 20.4 |
| rule verdicts overturned | 5 |

### Why facts were rejected

| reason | count |
|---|---:|
| `table_association_unverifiable` | 76 |
| `evidence_too_short` | 20 |
| `value_present_but_quote_unverifiable` | 1 |

### Where the adjudicator overturned the deterministic verdict

The most useful place to look for reasoning errors on either side.

### 1. RELATED  ·  confidence 1.00  ·  same document  ·  decided by `llm`  ·  explained by **basis**

**Fact A — Delhivery Limited · PTL freight tonnage growth**

- Value as printed: `20.8%`
- Normalized: `20.80 %`
- Period: `Q4 FY24` → `Q4 FY2024`
- Qualifiers: `basis=YoY`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 7

> YoY: 20.8% / QoQ: 8.6%

**Fact B — Delhivery Limited · PTL freight tonnage growth**

- Value as printed: `8.6%`
- Normalized: `8.60 %`
- Period: `Q4 FY24` → `Q4 FY2024`
- Qualifiers: `basis=QoQ`
- Source: `03-delhivery-q4-fy24-earnings-presentation.pdf`, page 7

> YoY: 20.8% / QoQ: 8.6%

**System reasoning.** The facts represent the same metric for the same period but measured against different baselines: Fact A is Year-over-Year growth, while Fact B is Quarter-over-Quarter growth. They are complementary data points in a time series. Supporting words: “YoY: 20.8% / QoQ: 8.6%”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover Q4 FY2024 |
| units | `%` ↔ `%` (comparable) |
| values compared | `20.8` vs `8.6` |
| relative difference | `58.6538%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `0.5814%` (from how precisely each figure is written) |
| ratio A/B | `2.4186` |
| qualifier `basis` | A=`YoY` · B=`QoQ` |
| hypothesis 1 | stated basis differs (YoY vs QoQ), a basis difference |
| rule-based verdict | `RECONCILED` — **overturned** by the adjudicator |

</details>

### 2. RECONCILED  ·  confidence 1.00  ·  same document  ·  decided by `llm`  ·  explained by **definition**

**Fact A — Delhivery Limited · net working capital cycle**

- Value as printed: `38`
- Normalized: `38.00 days`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 8

> In FY24, we shrunk our receivables days by 11 days, reducing our net working capital cycle from 38 to 31 days.

**Fact B — Delhivery Limited · net working capital cycle**

- Value as printed: `31`
- Normalized: `31.00 days`
- Period: `FY24` → `FY2024`
- Source: `02-delhivery-annual-report-fy24-excerpt.pdf`, page 8

> In FY24, we shrunk our receivables days by 11 days, reducing our net working capital cycle from 38 to 31 days.

**System reasoning.** The facts are not contradictory; they describe the beginning and end points of a change during the period. Fact A refers to the starting value of the net working capital cycle, while Fact B refers to the ending value after the reduction occurred during FY24. Supporting words: “reducing our net working capital cycle from 38 to 31 days”

<details><summary>Mechanical observations the decision rests on</summary>

| observation | value |
|---|---|
| period relation | `EQUAL` — both cover FY2024 |
| units | `days` ↔ `days` (comparable) |
| values compared | `38` vs `31` |
| relative difference | `18.4211%` |
| verdict on that | **outside** rounding tolerance |
| rounding tolerance | `1.6129%` (from how precisely each figure is written) |
| ratio A/B | `1.22581` |
| rule-based verdict | `CONTRADICTS` — **overturned** by the adjudicator |

</details>

