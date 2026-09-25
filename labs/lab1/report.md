# Lab 1 Report: The Reliable Extractor
**Course:** AI in Practice (Module 1)  
**Task:** Robust Structured Extraction from Semi-Structured Customer Support Tickets  
**Model Profile:** `gemini` (`gemini-3.5-flash-lite`)  
**Evaluator Run Split:** `dev` (60 tickets) & `test` (120 tickets)  

---

## the Part A failure table

In Part A, we evaluated `v0_naive.py` on $N=40$ tickets using an unconstrained prompt asking the model to output a raw JSON dictionary without JSON-schema enforcement or repair loops.

### Failure Breakdown and Taxonomy Mapping

| Failure Mode | Count in 40 | Example Ticket ID | T1 §3 Taxonomy Failure |
|---|:---:|:---:|---|
| **Not valid JSON at all** | 0 | — | *Failure 5: Malformed output* |
| **JSON wrapped in a markdown fence** (` ```json ... ``` `) | 40 | `T0001`, `T0002` | *Failure 5: Malformed output* (Transport/Formatting) |
| **Extra prose before or after the JSON** | 0 | — | *Failure 5: Malformed output* |
| **Valid JSON, missing a required field** | 0 | — | *Failure 7: Instruction omission / Schema violation* |
| **Valid JSON, category outside the allowed set** | 38 | `T0001`, `T0003` | *Failure 6: Schema violation* |
| **Urgency as a string instead of an int** | 40 | `T0001`, `T0002` | *Failure 6: Schema violation* |
| **Policy number invented (not in text)** | 0 | — | *Failure 8: Hallucination* |
| **Unhandled exception** | 0 | — | *Host Runtime Failure* (Infrastructure/Client) |

### The Core Arc
- **0/40 parsed strictly** by `json.loads` because the model deterministically wrapped all outputs in markdown backtick fences (` ```json `).
- **40/40 parsed after a 1-line regex/strip fix**, revealing the latent payload defects.
- **Still 0/40 clean** because 40/40 emitted `urgency` as descriptive strings (e.g. `"high"`, `"medium"`) rather than integer scale `1–5`, and 38/40 emitted open-ended categories (e.g. `"renewal"`, `"inquiry"`, `"grievance"`) outside the 6-class schema.
- **Zero Hallucination / Zero Omission**: The model did not invent policy numbers ($0/40$) or omit keys ($0/40$), demonstrating strong base compliance but an inability to adhere to implicit types without strict JSON schema contracts.

### Taxonomy Misfits
Two rows in the table do not map cleanly to the nine cognitive failure modes in T1 §3:
1. **Markdown Fence Wrapping**: This is a transport/presentation convention adopted during RLHF chat fine-tuning, rather than an underlying model reasoning failure.
2. **Unhandled Exception**: This represents an application/client host crash (e.g., HTTP timeout, unhandled socket error), which belongs to system runtime resilience rather than model cognitive failure.

### Human Reviewer Noticeability in Production
- **Noticeable Failures**: Hard syntax crashes, unhandled HTTP exceptions, and missing mandatory fields are immediately noticeable because the application or UI fails conspicuously.
- **Silent Failures (The Dangerous Ones)**: String urgencies (`"high"` coerced to `0` or dropped), plausible invented categories (`"refund"` instead of `billing`), boundary off-by-one urgency shifts (`2` vs `3`), and unflagged PII inside email signatures look deceptively normal to a human reviewer glancing at tickets, quietly corrupting database queues and SLA compliance.

---

## Structural Evolution & Boundary Design (Part B & C)

### 2.1 Schema Design & Evidence Placement (Part B)
- **Schema Constraints**: Implemented `TicketRecord` with strict `Literal` types for `category`, `sentiment`, `product`, and `language`. `urgency` was bounded to `1..5` with explicit anchor definitions in field descriptions. `policy_number` was bounded with regex `r"^AUR-\d{7}$"`.
- **Evidence Placement Rationale (T2 §3.3)**: `evidence: str` was placed **before** `category` in the Pydantic class definition. Because autoregressive transformers generate tokens left-to-right, placing the rationale/evidence span *first* forces the attention mechanism to attend to the raw ticket context and output justification tokens *before* committing probability mass to the classification label `category`.
- **Reliability Contract**: Wrapped `extract_b` and `extract_c` in resilient exception handlers catching `(StructuredOutputError, Exception)`. Failures never crash the host process; instead, they gracefully degrade to fallback records with `needs_human_review=True`.

### 2.2 Boundary Design: Moving Work Out of the Model (Part C)
Three fields were identified as deterministic or business-rule driven and removed from the model's extraction responsibility:
1. **`policy_number`**: Extracted via compiled regex `\bAUR-\d{7}\b`.
   - *Quoted Thread Trap*: When customers forward previous emails containing older policy numbers below the quote marker (`>`), naive regex captures the wrong policy. We split on standard reply/forward markers (`\n>`, `-----Original Message-----`, `---------- Forwarded message ----------`) and search only the *live ticket body*.
2. **`contains_pii`**: Extracted using deterministic regex patterns for Indian phone numbers (`\b[6-9]\d{9}\b`) and customer emails, explicitly filtering out Aurora's corporate support domain (`@aurorahealth.example`).
3. **`escalate`**: Computed as a deterministic business rule: `urgency >= 4 or "ombudsman" in ticket.lower()`.
4. **Token & Cost Impact (`TicketRecordC`)**: Pruning these fields from the prompt and response schema reduced prompt size, eliminated model hallucination on policy numbers ($1.000$ accuracy), and reduced per-ticket output tokens.

---

## the variant comparison table (v0 / B / C) with quality, cost, p95

All variants were evaluated using `run_eval.py`. The official test split was run **exactly once** and persisted to `reports/lab1_test.json`.

### Variant Performance Summary Table

| Metric | Variant v0 (Naive) | Variant B (Dev Split) | Variant C (Dev Split) | Variant C (Official Test Split) |
|---|:---:|:---:|:---:|:---:|
| **Schema Validity** | 0.0000 (strict) | **1.0000** | **1.0000** | **1.0000** |
| **Field Accuracy** | 0.0000 | 0.8738 | **0.8938** | **0.7979** |
| **Record Accuracy** (All 8 correct) | 0.0000 | 0.3167 | **0.4667** | **0.2917** |
| **Needs Review Rate** | 1.0000 | 0.2667 | **0.0500** | **0.3417** |
| **Error Rate (Crashes)** | 0.0000 | **0.0000** | **0.0000** | **0.0000** |
| **Total Split Spend (USD)** | ~$0.0035 | $0.0152 | **0.0121** | **0.0380** |
| **Unit Cost / Ticket (USD)** | ~$0.000088 | $0.000253 | **0.000202** | **0.000317** |
| **Latency p50** | 410 ms | 620 ms | **0 ms (cached)** / 810 ms | **833 ms** |
| **Latency p95** | 780 ms | 1,411 ms | **4,808 ms** | **1,174 ms** |

---

## per-field accuracy and the category confusion matrix

### 4.1 Per-Field Accuracy Breakdown (Official Test Split, $N=120$)

| Field | Accuracy | Evaluation Type | Primary Defect Cause |
|---|:---:|:---:|---|
| **`policy_number`** | **1.0000** (120/120) | Deterministic (Regex) | Flawless live-body extraction; zero thread bleed. |
| **`contains_pii`** | **1.0000** (120/120) | Deterministic (Regex) | Correctly identified phone/email while ignoring corporate support email. |
| **`language`** | **0.9417** (113/120) | Model (`SMALL`) | Subtle Hinglish code-switching in mostly English sentences. |
| **`product`** | **0.8500** (102/120) | Model (`SMALL`) | Indirect plan mentions defaulting to `"unknown"`. |
| **`escalate`** | **0.8417** (101/120) | Business Rule | Cascaded errors from model urgency classification shifts. |
| **`category`** | **0.6333** (76/120) | Model (`SMALL`) | Genre overlap between `complaint` vs `claims`/`billing`. |
| **`sentiment`** | **0.6333** (76/120) | Model (`SMALL`) | Calibration between `neutral` vs `frustrated` in polite demands. |
| **`urgency`** | **0.4833** (58/120) | Model (`SMALL`) | Subjective scale drift (off-by-one errors at boundaries 2 vs 3). |

### 4.2 Category Confusion Matrix ($N=120$)
*(Rows = Gold Annotated Label, Columns = Model Predicted Label)*

```
                       billing         claims      complaint    information  policy_change      technical
billing                     10              .              3              3              .              .
claims                       .              7              3             11              .              .
complaint                    .              1              7              8              .              .
information                  .              .              .             22              .              .
policy_change                .              .              1              5             16              .
technical                    .              .              1              8              .             14
```

#### Observations:
- **`information` as an Attractor**: `information` absorbed 11 `claims`, 8 `complaints`, 5 `policy_changes`, and 8 `technical` queries when users asked informational questions regarding underlying domain entities (e.g. "How do I submit claims bills?" or "What documents are needed to add my mother?").
- **`complaint` Boundary Leakage**: Angrily worded tickets reporting billing double-debits were frequently classified as `complaint` rather than `billing`.

---

## top three error clusters with proposed fixes

Audit of 15 failing test cases (`T0049`, `T0047`, `T0208`, `T0009`, `T0177`, `T0109`, `T0088`, `T0144`, `T0093`, `T0232`, `T0202`, `T0129`, `T0180`, `T0178`, `T0050`) reveals three dominant error clusters:

### Cluster 1: Subjective Urgency Boundary Sensitivity (62 / 120 failures)
- **Root Cause**: The model consistently over-indexes on technical distress (e.g. app crashes or login OTP delays) predicting `urgency=3`, whereas the gold standard defines technical app glitches as routine (`urgency=2`). Conversely, it under-indexes on statutory timelines (e.g. post-hospitalisation 60-day bill submission windows), predicting `urgency=2` where the standard requires `urgency=3`.
- **Proposed Fix**: Provide concrete anchored few-shot exemplars in the system prompt establishing that app crashes without immediate admission deadlines are `urgency=2`, and explicit statutory claim countdowns are `urgency=3`.
- **Estimated Gain**: $+15–20\%$ field accuracy on `urgency` (approx $+8–10\%$ overall record accuracy).

### Cluster 2: Topic vs. Genre Ambiguity in Categories (44 / 120 failures)
- **Root Cause**: When a user submits an aggressive inquiry regarding an operational failure (e.g., `T0129`: *"THIS IS THE THIRD TIME I am writing about the double debit on AUR-8245978"*), the model focuses on the emotional genre (`complaint`) rather than the core operational subject (`billing`).
- **Proposed Fix**: Implement hierarchical priority rules in the prompt: *operational subject takes precedence over emotional tone; `complaint` is reserved exclusively for formal service deficiency grievances where the underlying transaction cannot be routed to a specific operational team*.
- **Estimated Gain**: $+10–12\%$ category accuracy.

### Cluster 3: Code-Switched Hinglish Sentiment Miscalibration (44 / 120 failures)
- **Root Cause**: Mild Indian-English urgency phrases (e.g., *"Jaldi karo please"*, *"Kripya add my mother"*) triggered `sentiment="frustrated"`, whereas ground truth annotators treated colloquial particles as polite emphasis (`sentiment="neutral"`).
- **Proposed Fix**: Calibrate sentiment guidelines in the prompt: mandate that colloquial time particles like *"jaldi"* without aggressive capitalisation or hostile vocabulary do not warrant `"frustrated"`.
- **Estimated Gain**: $+8–10\%$ sentiment accuracy.

---

## the D5 economic argument

### Operational Parameters
- **Daily Volume**: 10,000 tickets/day $\rightarrow$ **3,650,000 tickets/year**.
- **Human Baseline**: 40 seconds per ticket triage @ ₹300/hour wage.
  $$\text{Human Cost / Ticket} = 40\,\text{s} \times \frac{₹300}{3600\,\text{s}} = ₹3.333\quad (\approx \$0.0392\text{ at } \$1 = ₹85)$$
  $$\text{Annual Manual Baseline Cost} = 3,650,000 \times ₹3.333 = \mathbf{₹12,166,667\text{ / year}}\quad (\approx \$143,137)$$

### Automated Pipeline Cost (Variant C)
- Measured unit cost per ticket on test split: **$0.000317 USD** ($\approx \mathbf{₹0.0269}$ INR).
- Annual LLM API spend: $3,650,000 \times \$0.000317 = \mathbf{\$1,157.25\text{ / year}}\quad (\approx \mathbf{₹98,366\text{ / year}})$.

### Break-Even Record Accuracy Derivation
In a human-in-the-loop triage system where an automated correct record saves a human triage interaction, and an unparsed/flagged record is routed to a human reviewer:
$$\mathbb{E}[\text{Cost per Ticket}] = C_{\text{LLM}} + (1 - A) \times C_{\text{human}}$$
For the automated system to deliver net positive return on investment ($\mathbb{E}[\text{Cost}] \le C_{\text{human}}$):
$$C_{\text{LLM}} + (1 - A) \times C_{\text{human}} \le C_{\text{human}} \implies A \ge \frac{C_{\text{LLM}}}{C_{\text{human}}}$$
$$\mathbf{A_{\text{break-even}}} = \frac{₹0.0269}{₹3.333} \approx \mathbf{0.0081}\quad (\mathbf{0.81\%})$$

### Business Conclusion
Because the cost of automated extraction ($\approx ₹0.027$) is less than $1\%$ of manual agent triage cost ($\approx ₹3.333$), the system breaks even at an extraordinarily low record accuracy of **0.81%**. At our achieved test record accuracy of **29.17%** (and field accuracy of **79.79%**), routing clean tickets straight to queue saves **~₹3.45 Million annually**, while reducing human triage backlog by over **1 Million tickets per year**.

---

## one thing you tried that did not work, and your explanation of why

### What We Tried
We initially attempted to improve `policy_number` recall by falling back to search quoted email threads (`>`) whenever no policy number was found in the live ticket body.

### Why It Failed
In multi-turn email chains where a customer inquiries about a *new* policy while replying to an old email thread regarding a *prior* closed policy, extracting from the quote block produced stale historical policy numbers. On the validation set, this introduced false-positive misattributions. 

### Resolution
We established the strict boundary rule: **only extract policy numbers from the unquoted live message body**. If the user does not mention a policy number in their current inquiry, `policy_number` must evaluate to `None`. This strict structural constraint yielded a perfect **120/120 (100.0%)** test accuracy on `policy_number`.