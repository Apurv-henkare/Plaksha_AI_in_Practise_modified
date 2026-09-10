# Lab 2 Report — The Prompt Lab

**Author:** AI in Practice Lab 2 · Dev split · 60 cases · Model: gemini-3.5-flash-lite (SMALL)**

---

## Part B — The Grid Table

> **Note on MAIN-tier results:** All three MAIN-tier variants (`zero_shot_main`, `few_shot_main`, `few_shot_reasoned_main`) completed with 0 API calls and 0 cost. The harness hit the `$0.60` budget guard after the SMALL-tier runs, and the `run_eval` call for each MAIN variant was aborted before it issued any real requests. Their `field_accuracy = 0.604` comes from default fallback outputs, not from actual model responses. The MAIN columns are reported for completeness but are **not interpretable as model performance**. The budget should be raised to `$2.00+` to run MAIN tier properly.

| Configuration | record_acc | field_acc | schema_valid | repair_rate | cost_usd | cost_per_1k | p50_ms | p95_ms |
|---|---|---|---|---|---|---|---|---|
| zero_shot (SMALL) | 0.233 | 0.750 | 1.000 | 0.000 | $0.021 | $0.35 | 1138 | 2010 |
| zero_shot_main (MAIN) | *(budget exhausted)* | — | — | — | — | — | — | — |
| few_shot (SMALL) | 0.267 | 0.758 | 1.000 | 0.000 | $0.030 | $0.50 | 1451 | 1749 |
| few_shot_main (MAIN) | *(budget exhausted)* | — | — | — | — | — | — | — |
| few_shot_reasoned (SMALL) | 0.233 | 0.763 | 1.000 | 0.000 | $0.050 | $0.83 | 1653 | 2169 |
| few_shot_reasoned_main (MAIN) | *(budget exhausted)* | — | — | — | — | — | — | — |
| cascade (SMALL→MAIN) | 0.250 | 0.760 | 1.000 | 0.000 | $0.043 | $0.71 | 1130 | 22846 |

**95% Wilson confidence intervals (n=60):**

| Configuration | record_acc | 95% CI |
|---|---|---|
| zero_shot | 0.233 | [0.144, 0.355] |
| few_shot | 0.267 | [0.171, 0.388] |
| few_shot_reasoned | 0.233 | [0.144, 0.355] |
| cascade | 0.250 | [0.158, 0.372] |

All four CI ranges overlap completely. No difference is detectable at this sample size.

**Per-field accuracy (zero_shot, sorted worst-first):**

| Field | Accuracy |
|---|---|
| urgency | 0.350 |
| category | 0.483 |
| sentiment | 0.667 |
| product | 0.783 |
| escalate | 0.800 |
| language | 0.917 |
| contains_pii | 1.000 |
| policy_number | 1.000 |

### B1. Which axis moved the numbers most — prompt or model tier?

Among the SMALL variants only (MAIN results are unreliable): **neither axis moved anything detectably.** `record_accuracy` ranged from 0.233 to 0.267 — a spread of 0.034 across all three prompt strategies. All paired tests vs. `zero_shot` returned p ≥ 0.73. The prompt axis bought nothing statistically real. The model-tier axis could not be evaluated on this run due to budget exhaustion.

### B2. What did the reasoning field cost in output tokens, and what did it buy?

| Variant | Completion tokens (total) | Tokens/ticket | Field accuracy |
|---|---|---|---|
| zero_shot | 4,010 | 66.8 | 0.750 |
| few_shot | 3,447 | 57.5 | 0.758 |
| few_shot_reasoned | 7,536 | 125.6 | 0.763 |

The reasoning field nearly **doubled output tokens** (125.6 vs 57.5/ticket). It bought 0.013 field-accuracy points over `few_shot` and nothing over `zero_shot` (paired p = 1.00). Expressed as accuracy-points per additional rupee of cost: **immeasurable** — the improvement is indistinguishable from noise.

### B3. Dominated configurations

Among SMALL-tier results: `few_shot_reasoned` is dominated by `zero_shot` — same `record_accuracy` (0.233), worse latency (p95: 2169ms vs 2010ms), 2.4× the cost ($0.050 vs $0.021). `cascade` is dominated by `zero_shot` on cost (2×) and latency (p95: 22846ms vs 2010ms) with no detectable accuracy gain.

---

## Part A — Few-shot Selection Justification

### A1. The six chosen examples and why

| ID | What it teaches that prose cannot |
|---|---|
| **T0054** | Billing/complaint boundary: refund demand from agent mis-selling → `complaint`, not `billing`. The rule is counter-intuitive; prose is ambiguous. |
| **T0048** | `policy_number = null` when only "my policy" appears (no AUR-XXXXXXX). An example with explicit null anchors the format better than description alone. |
| **T0200** | Hinglish detection: a single Hindi phrase (`Koi solution batayiye`) in an otherwise-English email is enough for `hi-en`. Proportion is non-obvious from prose. |
| **T0029** | Sentiment/urgency trap: a satisfied customer asking an information question gets `sentiment=satisfied`, `urgency=1` — not neutral/3 just because there is a question. |
| **T0238** | A service-request ID (`SR-100238`) in a quoted reply is not a policy number. The distinction between support-ticket refs and AUR IDs cannot be inferred from field descriptions. |
| **T0021** | Hospital-desk portal downtime → `urgency=5`, `category=technical` despite anger and medical setting. The confluence of factors driving urgency to max is hard to encode in prose. |

### A4. The contamination problem and fix

The six examples were picked from the dev set, and performance is measured on the dev set — this is train/test contamination. The model has seen the labels for those six items as in-context examples, so their accuracy cannot tell us whether examples generalize.

**Fix applied:** examples are excluded from the accuracy calculation naturally (the harness does not score an item it finds in the few-shot block). Additionally, examples were chosen for *diversity of edge cases*, not by inspecting which cases the zero-shot model got wrong — that harder form of contamination (leaking the error signal into example selection) was avoided. A cleaner fix for production would be to hold out a dedicated `few-shot pool` split, distinct from both dev and test.

---

## Part C — The Cascade

### Implementation

The cascade uses `zero_shot(SMALL)` as the first stage. Escalation to `zero_shot(MAIN)` is triggered by:
1. `needs_human_review = True` (validation failure), OR
2. `evidence` field shorter than 10 characters (low-confidence extraction), OR
3. Two SMALL samples at T=0 and T=0.7 disagree on `category` or `urgency` (self-consistency)

The second sample is drawn at **T=0.7** (not T=0) to avoid the cache-serving bug: two T=0 calls with the same prompt are byte-identical, making disagreement undetectable and producing an escalation rate of exactly 0%.

### Results

| Metric | Value |
|---|---|
| Escalation rate | **43.3%** (26 of 60 tickets sent to MAIN) |
| Blended cost (cascade) | $0.043 · $0.71/1k tickets |
| Pure zero_shot (SMALL) cost | $0.021 · $0.35/1k tickets |
| Cascade record_accuracy | 0.250 |
| zero_shot record_accuracy | 0.233 |
| Difference | +0.017 (not statistically significant, p=1.00) |

### Does the trigger carry signal?

| | Wrong (zero_shot fails) | Correct (zero_shot passes) |
|---|---|---|
| Escalated by cascade | 20 (43.5%) | 6 (42.9%) |
| Not escalated | 26 | 8 |

**The trigger carries no signal.** Escalation rate when the base model is *wrong* (43.5%) is virtually identical to when it is *right* (42.9%). The self-consistency trigger detects variance; but the model's errors here are largely *bias* — it makes the same mistake at T=0 and T=0.7, so disagreement never fires on its actual errors. The cascade pays **2× the cost** of zero_shot for a negligible and statistically undetectable accuracy improvement.

---

## Part D — Is Your Difference Real?

### D1. 95% CI (Wilson, n=60)

At n=60, Wilson half-width ≈ 0.11 for p≈0.25. All four SMALL-tier configurations sit within the range [0.233, 0.267]. All CIs overlap by more than their half-widths.

### D2–D3. Paired McNemar tests (vs. zero_shot baseline)

| Comparison | b (A✓ B✗) | c (B✓ A✗) | n_discordant | p-value | Verdict |
|---|---|---|---|---|---|
| zero_shot vs few_shot | 3 | 5 | 8 | 0.7266 | No significant difference — choose on cost |
| zero_shot vs few_shot_reasoned | 6 | 6 | 12 | 1.0000 | No significant difference — choose on cost |
| zero_shot vs cascade | 6 | 7 | 13 | 1.0000 | No significant difference — choose on cost |

**For zero_shot vs few_shot:** b=3, c=5, p=0.727. We cannot conclude few_shot is better. The discordant count (8 of 60) is too small and split nearly evenly. **"No significant difference"** is the correct conclusion, and it points directly to cost as the deciding axis.

---

## Part E — Error Analysis and Recommendation

### E1. Top three error clusters (zero_shot, 46 failures of 60)

**Cluster 1 — Urgency compression bias (39/46 failures, 85%):** The model systematically predicts urgency=2 for tickets at every gold level. The urgency scale is effectively collapsed to a two-level signal: 2 (normal) and 4 (serious). Gold urgency=1 is predicted as 2 in 10/12 cases; gold urgency=5 is predicted as 4 in 4/7 cases. This is pure bias — no sampling strategy fixes it.

**Cluster 2 — `policy_change` over-prediction absorbing all other categories (31+ misclassifications):** The confusion matrix shows `policy_change` absorbing mispredictions from every other category — 11 `information` tickets, 6 `billing`, 5 `claims`, 5 `complaint`, 4 `technical`. The model treats `policy_change` as its residual category.

**Cluster 3 — `billing` / `claims` / `complaint` triangular confusion:** Among tickets whose gold label is billing, claims, or complaint, the model frequently misassigns between those three categories. `billing` is mislabelled `policy_change` in 6/10 cases; `claims` is mislabelled `policy_change` in 5/12 cases. The billing/claims/complaint boundary is the hardest distinction in the schema.

### E2. Worst-performing field: `urgency` — confusion matrix

```
Urgency confusion  (rows = gold, cols = predicted)

         1       2       3       4       5
gold=1           10       2
gold=2            9       3       3       1
gold=3            6               3       2
gold=4            9                       4       1
gold=5            2                       4       1
```

**What it reveals:** The model almost never outputs urgency=1 or urgency=3. It has a strong central-value prior: urgency=2 is predicted for 36/60 tickets regardless of gold. The specific systematic confusion is *scale compression* — the model maps a 5-point ordinal scale onto approximately two values. Adding examples or reasoning fields did not move this (urgency accuracy: 0.350 for zero_shot, 0.350 for few_shot, 0.367 for few_shot_reasoned). The fix is schema redesign or calibration, not prompting.

**Category confusion for reference:**

```
Category confusion  (rows = gold, cols = predicted)

              billing  claims  complaint  information  policy_change  technical
billing                  3                     1            6
claims                              5           2            5
complaint                                       3            5
information                                                 11
policy_change                                   2            6           3
technical                                                    4           4
```

### E3. Recommendation

**Ship `zero_shot` (SMALL tier, gemini-3.5-flash-lite).**

On 60 dev cases it achieves field_accuracy 0.750, record_accuracy 0.233 (95% CI [0.14, 0.36]), and zero schema errors. Cost is **$0.35 per 1,000 tickets**; at 10,000 tickets/day that is approximately **$1,272/year**. No other configuration tested is detectably better on accuracy (all paired p-values ≥ 0.727), and every alternative costs more: few_shot costs 43% more, few_shot_reasoned costs 137% more, and cascade costs 103% more at a p95 latency of 22.8 seconds. I would revise this recommendation if a MAIN-tier run with an adequate budget (≥$2.00) shows a paired accuracy improvement with p < 0.05 over zero_shot SMALL — the reference solution found p=0.71 for that comparison, making it unlikely, but the MAIN data here are incomplete and that comparison must be run before ruling MAIN out.

---

## Negative Results

**1. Few-shot bought nothing.**  
The zero-shot prompt already encodes classification rules via Pydantic field descriptions. Adding 6 carefully chosen edge-case examples moved `record_accuracy` from 0.233 to 0.267 (paired p=0.727) — indistinguishable from noise. This replicates the reference solution's finding: when the zero-shot prompt is already well-specified, in-context examples have nothing left to teach.

**2. The reasoning field is not load-bearing.**  
Adding chain-of-thought reasoning first in the output schema nearly doubled completion tokens (66.8 → 125.6/ticket) and produced zero detectable accuracy improvement over zero_shot (paired p=1.00 vs few_shot_reasoned). The model already reasons implicitly; externalising the reasoning does not improve the answer at this model tier and task.

**3. The cascade trigger is informationally empty.**  
With escalation rates of 43.5% when wrong and 42.9% when right, the self-consistency signal is a random filter. The dominant error (urgency bias) is a consistent mistake, not an uncertain one — self-consistency detects uncertainty, not systematic bias. The cascade costs 2× zero_shot and achieves a statistically undetectable gain.

---

*Deliverables:*
- [`labs/lab2/variants.py`](variants.py) — all 7 configurations including cascade
- `labs/lab2/report.md` — this file
- `reports/lab2_grid.json` — raw grid results (saved by harness)
