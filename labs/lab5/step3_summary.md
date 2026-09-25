# Step 3 Summary: Implementing the Fix — One Variable at a Time (Part C)

---

## 1. The Big Picture (In Plain English)

In Step 1, our diagnosis proved that **85.7% of all failures were Generation Errors (Mode 6)**.  
In Step 2, our Expected-Value analysis proved that prompt refinement had the highest recovery potential at near-zero cost.

Now in **Step 3 (Part C)**, we put that plan into action.

The golden rule of engineering is:
> **Change ONLY ONE variable at a time.**

If you change the prompt, change the chunk size, and change the vector search all at once, you will never know which change actually helped or which one made things worse. So in this step, **we leave the retriever 100% untouched** and modify only the **Generation Prompt Contract (`ANSWER_SYSTEM`)**.

---

## 2. The Diagnosis of What Was Broken in the Prompt

In Lab 4, our system prompt had this rule:

```python
# The Old Rule 6 (The Culprit):
6. Conciseness: Be concise, direct, and factual. Keep answers to two or three sentences unless the question explicitly requires more detail.
```

### Why this rule broke 12 questions:
Insurance policy documents are legally complex. A typical rule consists of:
1. A baseline timeline or limit (*"Waiting period is 36 months"*),
2. An optional discount or reduction rider (*"Reduces to 12 or 24 months with rider"*),
3. An age-specific condition (*"24 months for seniors above 60"*).

When the AI was strictly ordered: *"Keep answers to two or three sentences"*, it was forced to make a trade-off. To stay within 2 sentences, the model **cut out the riders, skipped the age exceptions, and dropped secondary conditions**. The AI judge saw the missing rider and gave the answer partial credit (1/2) instead of full marks (2/2)!

Furthermore, on multi-hop questions with exact codes (like Q44 `AUR-HI-SIL-2026`), the AI got nervous about being able to answer concisely and refused the question entirely (0/2).

---

## 3. The Code Fix We Implemented in `labs/lab4/rag.py`

We updated `ANSWER_SYSTEM` with two targeted, high-precision changes:

### Change 1: Replaced the Brevity Penalty with Completeness
We deleted the 2–3 sentence limitation and replaced it with an explicit instruction to state all conditions, exceptions, and riders using structured bullet points:

```text
6. Completeness & Structure: Be comprehensive, direct, and factual. Always explicitly include all relevant conditions, exceptions, optional riders, age restrictions, and specific limits found in the sources. Use clear bullet points if multiple conditions or plan options apply, rather than omitting details for brevity.
```

### Change 2: Calibrated Refusal to Prevent Wrongful Refusals
We updated Rule 2 to ensure the model does not panic and refuse when product codes or partial plan details are present in the text:

```text
2. Refusal & Partial Grounding:
   - If the provided sources contain NO information to answer the question, output EXACTLY this string:
     "I don't have enough information in the provided sources to answer that."
   - If only PART of the question can be answered from the sources (e.g. coverage exists but limits are unstated), state the supported facts with citations, and state:
     "I don't have enough information in the provided sources to answer that." regarding the missing details. Do not guess or invent unmentioned limits.
   - However, if the sources contain the relevant facts, plan details, or product codes, extract and answer with the supported facts rather than refusing.
```

---

## 4. The Complete Updated Prompt Contract

```python
ANSWER_SYSTEM = f"""\
You answer questions using ONLY the numbered sources provided below.
Rules, in priority order:
1. Grounding: Answer strictly and exclusively from the provided numbered sources. Never use outside or general knowledge.
2. Refusal & Partial Grounding:
   - If the provided sources contain NO information to answer the question, output EXACTLY this string:
     "{REFUSAL}"
   - If only PART of the question can be answered from the sources (e.g. coverage exists but limits are unstated), state the supported facts with citations, and state:
     "{REFUSAL}" regarding the missing details. Do not guess or invent unmentioned limits.
   - However, if the sources contain the relevant facts, plan details, or product codes, extract and answer with the supported facts rather than refusing.
3. Citations: Every factual sentence or claim must end with a citation to the specific source(s) supporting it, formatted as [1] or [2][5].
4. Valid Indices: Never cite a source number that was not provided in the context (only cite numbers between 1 and the total number of sources).
5. Contradictions: If different sources contradict or disagree with each other, explicitly describe the discrepancy and cite all conflicting sources.
6. Completeness & Structure: Be comprehensive, direct, and factual. Always explicitly include all relevant conditions, exceptions, optional riders, age restrictions, and specific limits found in the sources. Use clear bullet points if multiple conditions or plan options apply, rather than omitting details for brevity.
{UNTRUSTED_SYSTEM_CLAUSE}
"""
```

---

## 5. Glossary: What Each Term Means (In Simple Plain English)

To understand the engineering behind this fix:

- **Single-Variable Discipline:**  
  The experimental rule that you must change only one component at a time. If we changed both the prompt and the retriever simultaneously, any improvement or drop would be scientifically untraceable.
- **Prompt Contract:**  
  The formal agreement between the software engineer and the AI model that governs how the model extracts information, when it must refuse, and how it must format its answers.
- **Completeness vs. Brevity Trade-Off:**  
  The fundamental tension in RAG generation: forcing models to write short answers causes them to drop legal exceptions, while allowing comprehensive answers uses slightly more tokens.
- **Refusal Calibration:**  
  Fine-tuning the prompt instructions so the AI model declines genuinely unanswerable questions (avoiding hallucination) without getting overly timid and refusing valid questions.
- **Structured Output (Bullet Points):**  
  Allowing the AI model to use bulleted lists so that multi-part insurance rules (e.g. waiting periods + optional riders + age limits) can be stated clearly without getting tangled in conversational prose.

---

## 6. Key Takeaways from Step 3

1. **The fix was applied cleanly:** We modified only `ANSWER_SYSTEM` in `labs/lab4/rag.py`.
2. **Retriever was untouched:** Preserving single-variable discipline.
3. **Ready for Step 4:** In Part D, we will re-run the 45-question evaluation, compare our results directly against the Lab 4 baseline in a Before/After table, and perform a full Regression Check.
