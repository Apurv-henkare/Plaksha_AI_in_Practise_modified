# Lab 1, Part A: Answers to `v0_naive.py` Diagnostic Questions

This document provides complete, rigorous answers to the three core diagnostic questions printed at the end of `labs/lab1/v0_naive.py` (lines 197–203).

---

## Question 1
> **"Which of these are in the T1 §3 taxonomy, and which two are not?"**

### Mapping of v0 Failure Modes to T1 §3 Taxonomy

| Failure Mode in `v0_naive.py` | Count in 40 | T1 §3 Cognitive Taxonomy Mapping | Notes & Classification |
|---|:---:|---|---|
| **Not valid JSON at all** / `malformed_json` | 0 | **Failure 5: Malformed Output** | Syntactic decoding failure where raw string cannot be parsed as valid JSON. |
| **JSON wrapped in markdown fence** (` ```json `) | 40 | **NOT in T1 §3 Taxonomy** *(Taxonomy Misfit 1)* | A formatting/transport artifact from RLHF chat fine-tuning (Markdown presentation wrapper), not a model reasoning failure. |
| **Extra prose before or after JSON** | 0 | **Failure 5: Malformed Output** | Conversational preamble/postamble ("Here is your JSON:") breaking strict parsers. |
| **Valid JSON, missing a required field** | 0 | **Failure 7: Instruction Omission** | Incomplete response omitting required dictionary keys. |
| **Category outside allowed set** | 38 | **Failure 6: Schema Violation** | Emits open-ended strings (e.g. `"renewal"`, `"grievance"`, `"inquiry"`) violating categorical discrete domain constraints. |
| **Urgency as a string instead of an int** | 40 | **Failure 6: Schema Violation** | Emits string descriptors (e.g. `"high"`, `"medium"`) instead of integer scale `1..5`. |
| **Policy number invented (not in text)** | 0 | **Failure 8: Hallucination** | Fabricating an identifier not grounded in the source text. |
| **Unhandled exception** | 0 | **NOT in T1 §3 Taxonomy** *(Taxonomy Misfit 2)* | An infrastructure/client runtime crash (e.g., HTTP connection timeout, API 429 rate limit, network socket drop), belonging to systems resilience. |

### The Two Non-Taxonomy Rows:
1. **Markdown Fence Wrapping (` ```json ... ``` `)**: Modern instruction-tuned LLMs are trained to format structured snippets inside markdown blocks for chat display. This is a transport-layer convention rather than an algorithmic reasoning failure.
2. **Unhandled Exception**: Host process or network crashes represent infrastructure/environment failures, outside the model's cognitive failure taxonomy.

---

## Question 2
> **"Fixing ONE line in `extract_v0` takes you from 0/40 parsed to 40/40 parsed (after stripping markdown fences) — but only 0/40 CLEAN. Why is that second number the entire justification for Part B?"**

### The Core Arc: Syntactic Parsing vs. Semantic Conformance

When running `v0_naive.py`, stripping markdown fences with a 1-line regex/salvage fix allows `json.loads` to parse 100% of the responses ($40/40$). However, inspecting the contents reveals that **0 out of 40 records are actually clean or production-usable**:
- **40/40 emitted `urgency` as a string** (e.g. `"high"`, `"urgent"`), which crashes database ingestion pipelines expecting integer types `1..5` and breaks numeric sorting/SLA queue math.
- **38/40 emitted open-ended categories** (e.g. `"renewal"`, `"inquiry"`, `"grievance"`, `"escalation"`), violating the 6-class routing contract and causing silent routing failures.

### Why This is the Entire Justification for Part B:
A naive fix (tolerant parsing / string stripping) only solves the **syntax transport layer**—it gets the payload through `json.loads()`. It provides **zero guarantees** about:
1. **Type Safety**: Bounding variables to integers, booleans, or specific object shapes.
2. **Domain Constraints**: Restricting fields to closed enumeration sets (`Literal[...]`).
3. **Value Range Anchors**: Bounding numerical scores (`ge=1, le=5`).
4. **Self-Correction**: Re-prompting with validation error feedback when the model violates the schema contract.

**Part B (Pydantic schema definitions, constrained generation, and the validation-repair loop)** exists because *syntactic validity is meaningless without semantic contract conformance*.

---

## Question 3
> **"Which of these would a human reviewer even notice in production?"**

In a production operations environment, errors split into **obvious hard failures** and **silent insidious failures**:

### 1. What a Human Reviewer WOULD Easily Notice:
- **Hard Parser Crashes / Unhandled Exceptions**: The UI crashes or displays an error banner ("Failed to process ticket").
- **Missing Required Fields**: A blank or empty field in the triage queue interface is immediately obvious to a reviewer.
- **Gross Hallucinations**: An invented policy number like `AUR-9999999` that fails CRM database lookup triggers an immediate system alert.

### 2. What a Human Reviewer WOULD NOT Easily Notice (The Silent Killers):
- **Type Coercion / Schema Drift**: If a downstream service attempts to coerce string `"high"` to integer `0` (or defaults to `None`), urgency is silently lost without an error banner, causing high-priority tickets to languish.
- **Plausible Category Hallucinations**: When the LLM outputs category `"inquiry"` or `"refund"`, a human reviewer skimming the text might think *"Yes, this is an inquiry about a refund"*, failing to realize that the formal enterprise taxonomy requires `billing` or `claims`. The ticket looks sensible to a human eye but is dropped into the wrong automated backend queue.
- **Boundary Off-By-One Urgency Errors (`urgency=2` vs `urgency=3`)**: Unless human reviewers have memorized the 15-page annotation manual, they cannot easily tell whether an issue qualifies as a routine SLA 2 or a delayed SLA 3. These subtle calibration errors pass casual inspection while violating statutory turnaround times.
- **Subtle PII Omission in Signature Blocks**: Phone numbers or personal emails buried in multi-line email signature footers are easily missed by human reviewers skimming for the core complaint, creating silent compliance/privacy violations.
