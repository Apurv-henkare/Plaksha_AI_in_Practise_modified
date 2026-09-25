# Lab 5 Final Report: RAG v2 — Diagnose, Fix, Prove

**Dataset:** Aurora Health Policy Corpus (30 documents, 14 distractors)  
**Evaluation Set:** 45 golden questions (`data/eval/rag_golden.jsonl`; 40 answerable, 5 unanswerable)  
**Baseline System:** Lab 4 RAG Pipeline (`reports/lab4.json`)  
**New Evaluated System:** Lab 5 System with Updated Prompt (`reports/lab5.json`)  
**Data Files Generated:** `reports/lab5_diagnosis.json`, `reports/lab5_before_after.json`

---

## Executive Summary

In Lab 4, our health insurance question-answering system got roughly 1 out of every 5 questions wrong (14 failures out of 45). 

When an AI makes mistakes, most developers start guessing: they try bigger models, switch databases, or tweak search settings. In Lab 5, we took a medical approach: **diagnose the disease before prescribing medicine**.

We discovered that **almost 86% of all mistakes were caused by the AI writer dropping important rules to keep its answers short**. We fixed the prompt, re-tested all 45 questions, and measured what improved and what got worse.

---

## the failure tally and the Pareto chart

We ran our automated diagnostic tool (`labs/lab5/diagnose.py`) on all 14 failed questions from Lab 4. The tool checked each question step-by-step to find out exactly where it failed:

### Failure Mode Tally (Lab 4 Baseline = 14 Failures)

| Mode | Where the Pipeline Failed | Count ($n$) | Share (%) | What This Means in Plain English |
|:---:|---|:---:|:---:|---|
| **6** | **Generation Error** | **12** | **85.7%** | The search engine found the right page, but the AI writer forgot to mention riders, age limits, or conditions. |
| **4** | **Ranking Error** | **2** | **14.3%** | The right page was found in the top 30, but ranked just outside the top 5 (Q35 and Q37). |
| **1** | Missing Content | 0 | 0.0% | The facts were present in the documents for all answerable queries. |
| **2** | Chunk Boundary | 0 | 0.0% | Text slicing did not cut any legal sentences in half. |
| **3** | Embedding Mismatch | 0 | 0.0% | The vector search easily found the right topics in the top 30. |
| **5** | Reranker Error | 0 | 0.0% | We did not use a second-stage reranker. |
| **7** | Presentation Error | 0 | 0.0% | Our Python code caught and fixed all citation bracket errors. |

### The Pareto Chart

```text
failure mode          n    share   cumulative
generation           12   85.7%    85.7%  ██████████████████████████
ranking               2   14.3%   100.0%  ████
```

> **Plain English Takeaway:** Nearly all our problems (12 out of 14) were **Generation Errors**. The search engine did its job well, but the AI writer struggled to summarize complex legal rules accurately.

---

## your Part B ranking table and the justification for your pick

Before writing any code, we evaluated our two problem areas based on expected payoff, cost, speed, and effort:

### Expected-Value Comparison Table

| Problem Cluster | Failures ($n$) | What We Plan to Fix | Expected Recoveries | Cost Impact | Speed Impact | Effort Needed |
|---|:---:|---|:---:|:---:|:---:|:---:|
| **Mode 6 (Generation)** | **12** (85.7%) | **Relax Brevity & Require Complete Bullet Points:** Remove the 2–3 sentence limit. Instruct the AI to explicitly list all conditions, riders, and age rules in bullet points. | **4 to 6 questions** | $\approx +\$0.0010$ per query (a few extra words) | $+600$ ms | **Low** (edit the prompt in `rag.py`) |
| **Mode 4 (Ranking)** | **2** (14.3%) | **Widen Search Pool (`final_k`):** Retrieve the top 10 chunks instead of top 5. | **0 to 1 question** (Q37 limit is missing from corpus, so only Q35 could possibly benefit) | $\approx +\$0.0001$ per query | $+50$ ms | **Low** (change one setting) |

### One-Sentence Justification for Our Pick:
> *"We chose **Mode 6 (Generation)** because it causes **85.7% of all our system's failures (12 out of 14)** even though the search engine already found the right pages, making prompt improvement the highest-impact and lowest-cost fix."*

---

## your prediction, and what actually happened

### What We Predicted in Advance (Recorded in Step 2):
> *"By telling the AI to write structured bullet points and removing the strict 2–3 sentence limit, we predict our fix will recover **4 to 6 of the 12 generation failures**, lifting our overall correctness score by **+0.05 to +0.08 points** (from 0.800 to ~0.850–0.880)."*

### What Actually Happened in Reality:
* **The Recoveries:** The fix successfully healed **3 difficult questions** (Q19, Q23, and Q35) that previously failed.
* **The Regressions:** However, the fix caused **3 previously passing questions** (Q24, Q25, and Q42) to drop by 1 point because the AI wrote too much unnecessary background text.
* **The Net Result:** Our overall correctness score stayed flat at **0.800 ($\Delta = +0.000$)**.
* **The Refusal Side-Effect:** Refusal precision dropped from **0.625 to 0.556 (−0.069)** because being told to be thorough made the AI overly cautious, causing it to refuse 1 question it should have answered.

---

## the D1 before/after table

We re-tested all 45 benchmark questions using our calibrated AI judge model (`gemini-2.5-pro`):

| Metric | Target | Lab 4 Baseline ($v_1$) | Lab 5 New ($v_2$) | Change ($\Delta$) | Target Met? |
|---|:---:|:---:|:---:|:---:|:---:|
| **Answer Correctness** | $\ge 0.750$ | **0.800** | **0.800** | **+0.000** | **YES (80.0%)** 🎯 |
| **Faithfulness** | $\ge 0.900$ | **0.978** | **0.978** | **+0.000** | **YES (97.8%)** 🚀 |
| **Citation Validity** | **1.000** | **1.000** | **1.000** | **+0.000** | **PERFECT (100%)** 🎯 |
| **Refusal Recall** | $\ge 0.800$ | **1.000 (5/5)** | **1.000 (5/5)** | **+0.000** | **PERFECT (100%)** 🎯 |
| **Refusal Precision** | $\ge 0.700$ | **0.625 (5/8)** | **0.556 (5/9)** | **−0.069** | **REGRESSED ⚠️** |
| **p95 Latency** | $\le 6,000$ ms | **4,658 ms** | **5,261 ms** | **+603 ms** | **PASS ⚡** |
| **Cost per Query** | $\le 2\times$ base | **\$0.0101** | **\$0.0111** | **+\$0.0010** | **PASS 💰** |

---

## the D2 regression check, including anything that got worse

In real engineering, fixing one thing often breaks something else. Here is an honest look at what helped and what hurt:

### 1. The 3 Questions That Improved:
* **Q19 (Silver Room Rent Calculation):** *Score improved from 1/2 $\rightarrow$ 2/2 (Full Marks).*  
  In Lab 4, the AI calculated the 0.667 deduction ratio but cut out the list of exempt consumables to stay under 2 sentences. With bullet points allowed, it included everything.
* **Q23 (Lasik and Out-Patient Coverage):** *Score improved from 0/2 $\rightarrow$ 1/2.*  
  Previously, the AI panicked and refused completely. Now it correctly extracts the OPD rider exclusion rule.
* **Q35 (Dental Treatment Exclusions):** *Score improved from 0/2 $\rightarrow$ 1/2.*  
  The AI successfully combined the accident exception and out-patient rules into one clear answer.

### 2. The 3 Questions That Got Worse:
* **Q24 (Policy condition):** *Score dropped from 2/2 $\rightarrow$ 1/2.*
* **Q25 (Waiting period rule):** *Score dropped from 2/2 $\rightarrow$ 1/2.*
* **Q42 (Paraphrased claim rule):** *Score dropped from 2/2 $\rightarrow$ 1/2.*  
  *Why they dropped:* On these simpler questions, telling the AI to "be comprehensive" caused it to ramble and pull in unrelated background text from nearby sections, which the judge penalized.

### 3. Why Refusal Precision Got Worse (0.625 $\rightarrow$ 0.556):
When you tell an AI to always include every single detail, its standards go up. If a retrieved passage was missing even a small secondary detail, the AI decided to say *"I don't have enough information"* instead of answering the main question. This caused total refusals to rise from 8 to 9, lowering our precision.

---

## the D3 re-classification

We re-ran our diagnostic classifier on the 16 questions that still have imperfect scores in Lab 5:

| Failure Mode | Initial Lab 4 Count ($v_1$) | Remaining Lab 5 Count ($v_2$) | Net Change | Share of Remaining Errors |
|---|:---:|:---:|:---:|:---:|
| **Mode 6: Generation Error** | 12 | **15** | +3 | **93.8%** |
| **Mode 4: Ranking Error** | 2 | **1** | -1 | **6.2%** |
| **All Other Modes (1, 2, 3, 5, 7)**| 0 | **0** | 0 | **0.0%** |
| **Total Imperfect Questions** | **14** | **16** | **+2** | **100.0%** |

```text
Updated Pareto Chart (Remaining Failures):
generation           15   93.8%   93.8%  ████████████████████████████
ranking               1    6.2%  100.0%  ██
```

> **Plain English Takeaway:** Mode 6 is still our biggest bottleneck ($93.8\%$). Ranking errors dropped from 2 to 1 because better generation helped rescue Q35. Until we give the AI better structured reasoning tools, changing the search engine will not help much.

---

## the fix that did not work, with its number

* **The Fix We Tried:** Removing the 2–3 sentence brevity limit and telling the AI to always write exhaustive bullet points.
* **The Measured Result:** **Net Correctness Change = +0.000** and **Refusal Precision Change = −0.069**.
* **Why It Did Not Move the Overall Score:**  
  The fix was a double-edged sword. It helped complex questions that needed extra room to breathe (gaining +3 points on Q19, Q23, and Q35), but it hurt simple questions by encouraging the AI to add unnecessary fluff (losing −3 points on Q24, Q25, and Q42). The gains and losses cancelled each other out completely.

---

## 8. Strategic Discussion & Core Course Questions

1. **Prediction vs. What Actually Happened:**  
   Our prediction was right about *how* to fix multi-part questions, but we forgot that unconstrained prompts let models over-generate on simple questions. A better fix for Lab 6 would be adaptive: write bullet points for multi-part questions, but keep simple questions concise.
2. **Why Removing the Brevity Rule Lowered Refusal Precision:**  
   When an AI is told to include all conditions and limits, it becomes afraid of giving an incomplete answer. If a passage mentions a benefit but leaves out a minor limit, the AI refuses entirely rather than sharing what it knows.
3. **Did the Largest Cluster Win the Expected-Value Test?**  
   Yes. Mode 6 (12 errors) had the highest potential payoff for near-zero cost. Mode 4 only had 2 errors, and one of them (Q37) was impossible to answer anyway because the information is not in the documents. Mode 6 was definitely the right place to focus.
4. **Which Mode Cannot Be Fixed by Prompting or Search?**  
   **Mode 1 (Missing Content).** If a rule or number does not exist in the policy PDFs (like the Singapore coverage limit in Q37), no AI prompt and no search algorithm can find it. The only way to fix Mode 1 is **data curation**—having a human upload the missing document.
