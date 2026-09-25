# Step 1 Summary: Failure Diagnosis & The Pareto Chart (Part A)

---

## 1. The Big Picture (In Plain English)

In Lab 4, our health insurance question-answering system achieved an 80% correctness score. That is a solid foundation, but it means that **roughly 1 in 5 questions (14 out of 45) failed**.

When an AI system gets a question wrong, amateur developers usually start guessing:
- *"Maybe we should change the embedding model?"*
- *"Maybe we should switch vector databases?"*
- *"Maybe we should make the chunks bigger?"*

That approach is called **thrashing**. It burns weeks of engineering time without solving the real problem.

In **Lab 5 (Step 1)**, we took a disciplined, medical approach: **diagnosis before treatment**.  
Every single failure happens at **exactly one stage** of the pipeline. We built a Python diagnostic tool (`diagnose.py`) that acts like an automated investigator, walking through a formal decision tree to find the exact root cause of every single wrong answer.

---

## 2. The 7 Suspects (The 7 Failure Modes)

Whenever a RAG system answers incorrectly, exactly one of these 7 things went wrong:

```text
+----------------------------------------------------------------------------------------------------+
|                                    THE 7 RAG FAILURE MODES (T4 §5)                                  |
+----------------------------------------------------------------------------------------------------+
|  Mode 1: Missing Content      | The facts do not exist in the policy documents at all.             |
|  Mode 2: Chunk Boundary       | Slicing text cut a sentence or rule right down the middle.          |
|  Mode 3: Embedding Mismatch   | The user's words and the document's words didn't match semantically.|
|  Mode 4: Ranking Error        | The right document was found in top 30, but ranked outside top 5.  |
|  Mode 5: Reranker Error       | A second-stage reranker mistakenly dropped the correct page.       |
|  Mode 6: Generation Error     | Right page was in top 5, but the AI Writer omitted details/rules.  |
|  Mode 7: Presentation Error   | Answer was factually right, but citation formatting broke.          |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. How the Diagnostic Decision Tree Works

In `labs/lab5/diagnose.py`, we implemented the formal diagnostic tree:

1. **Step 1 (Check Presentation):** Is the answer factually correct, but the citation brackets `[1]` are invalid? $\rightarrow$ **Mode 7 (Presentation)**.
2. **Step 2 (Check Content):** Does the information exist in the corpus files? If not $\rightarrow$ **Mode 1 (Missing Content)**.
3. **Step 3 (Check Context & Generation):** Did the search engine successfully bring the primary gold document into the AI's top 5?
   - If **YES**, the AI writer had the text in front of it and still scored $< 2$ or refused $\rightarrow$ **Mode 6 (Generation Error)**.
4. **Step 4 (Check Retrieval Top 30):** If the gold document was missing from the top 5, was it in the top 30?
   - If **YES** $\rightarrow$ **Mode 4 (Ranking Error)**.
5. **Step 5 (Check Vocabulary):** If missing from top 30, does searching the document's own text find it?
   - If **YES** $\rightarrow$ **Mode 3 (Embedding Mismatch)**.
   - If **NO** $\rightarrow$ **Mode 2 (Chunk Boundary - needs human check)**.

---

## 4. The Test Results

We ran the diagnostic script across all 45 questions from `reports/lab4.json`:

```powershell
python labs/lab5/diagnose.py --input reports/lab4.json --pareto
```

### What the Terminal Printed:

```text
14 failures out of 45

  Q04   generation           primary gold doc(s) retrieved in top 5, but generator produced score 1/2 (generation omission/reasoning)
  Q05   generation           primary gold doc(s) retrieved in top 5, but generator produced score 1/2 (generation omission/reasoning)
  Q10   generation           primary gold doc(s) retrieved in top 5, but generator produced score 1/2 (generation omission/reasoning)
  Q11   generation           primary gold doc(s) retrieved in top 5, but generator produced score 1/2 (generation omission/reasoning)
  Q19   generation           primary gold doc(s) retrieved in top 5, but generator produced score 1/2 (generation omission/reasoning)
  Q20   generation           primary gold doc(s) retrieved in top 5, but generator produced score 1/2 (generation omission/reasoning)
  Q21   generation           primary gold doc(s) retrieved in top 5, but generator produced score 1/2 (generation omission/reasoning)
  Q23   generation           primary gold doc(s) retrieved in top 5, but generator produced score 0/2 (generation omission/reasoning)
  Q26   generation           primary gold doc(s) retrieved in top 5, but generator produced score 1/2 (generation omission/reasoning)
  Q29   generation           primary gold doc(s) retrieved in top 5, but generator produced score 1/2 (generation omission/reasoning)
  Q32   generation           primary gold doc(s) retrieved in top 5, but generator produced score 1/2 (generation omission/reasoning)
  Q35   ranking              gold doc(s) ['outpatient-and-wellness'] in top 30, but ranked outside top 5 (ranking error)
  Q37   ranking              gold doc(s) ['exclusions', 'plans-overview'] in top 30, but ranked outside top 5 (ranking error)
  Q44   generation           primary gold doc(s) retrieved in top 5, but generator produced score 0/2 (generation omission/reasoning)

failure mode          n    share   cumulative
generation            12   85.7%   85.7%  ██████████████████████████
ranking                2   14.3%   100.0%  █
```

---

## 5. Analyzing the Findings

The Pareto chart reveals three massive takeaways:

1. **A Classic Pareto Distribution (85/15 Rule):**  
   Out of 7 possible failure modes, **100% of our defects are concentrated in just TWO modes**:
   - **Mode 6 (Generation): 12 failures (85.7%)**
   - **Mode 4 (Ranking): 2 failures (14.3%)**
2. **Our Lab 3 Search Engine is Nearly Flawless:**  
   Zero failures in Mode 1 (missing content), zero in Mode 2 (chunk boundary), zero in Mode 3 (embedding mismatch), and zero in Mode 7 (presentation). In almost every single failure, **the search engine successfully delivered the right document into the top 5!**
3. **The True Bottleneck is the AI Writer:**  
   In **12 out of 14 cases**, the AI model (`gemini-2.5-flash`) had the exact right policy document on its desk, but it lost points because:
   - It cut out important clauses (like pre-existing condition riders or age rules) to obey the strict *"2 to 3 sentences"* prompt rule.
   - It got overly cautious on multi-hop questions (e.g. Q23 and Q44) and refused to answer.

---

## 6. Glossary: What Each Term Means (In Simple Plain English)

To make sure every concept in Step 1 is crystal clear:

- **Failure Diagnosis:**  
  The engineering practice of inspecting a broken answer to find the single component (data, chunker, retriever, reranker, or generator) that caused the defect.
- **Diagnostic Decision Tree:**  
  A strict, step-by-step flowchart where each test eliminates one possibility until only the true root cause remains.
- **Pareto Principle (80/20 Rule):**  
  The real-world principle that roughly 80% of problems are caused by 20% of causes. In our test, **85.7% of all defects were caused by a single stage: Generation (Mode 6)**.
- **Pareto Chart:**  
  A descending bar graph that visually shows which problems are the biggest, making it immediately obvious where engineers should focus their effort.
- **Mode 1 (Missing Content):**  
  When an AI cannot answer because the necessary facts were never included in the document library.
- **Mode 2 (Chunk Boundary):**  
  When document slicing cuts across sentences or separates a rule from its condition.
- **Mode 3 (Embedding Mismatch):**  
  When the vector search fails because the user's phrasing is too different from the document's vocabulary.
- **Mode 4 (Ranking Error):**  
  When the retriever finds the right document in the top 30 candidates, but fails to rank it inside the top 5.
- **Mode 5 (Reranker Error):**  
  When an additional reranking model drops a good document that was already in the top 5.
- **Mode 6 (Generation Error):**  
  When the search engine successfully brings the right document into the prompt, but the language model misreads, omits conditions, summarizes too aggressively, or hallucinates.
- **Mode 7 (Presentation Error):**  
  When the text is accurate, but citation bracket rules (like `[1]`) are violated.

---

## 7. Key Takeaways from Step 1

1. **Diagnosis before treatment works:** We did not waste time guessing or tuning embeddings.
2. **We identified the primary bottleneck:** Mode 6 (Generation) accounts for **85.7% of all defects (12 out of 14)**.
3. **Ready for Step 2:** In Part B, we will rank potential fixes by Expected Value and write down our formal pre-registered prediction before touching any code.
