# Step 2 Summary: Expected-Value Ranking & Pre-Registered Prediction (Part B)

---

## 1. The Big Picture (In Plain English)

In Step 1, our Pareto analysis revealed that our 14 failures are divided into two distinct defect clusters:
- **Mode 6 (Generation): 12 failures (85.7%)**
- **Mode 4 (Ranking): 2 failures (14.3%)**

Now comes the critical engineering question: **What should we fix first?**

Many teams make the rookie mistake of picking whatever fix seems most "fun" or "advanced" (such as adding a heavy cross-encoder or fine-tuning an embedding model).

In **Part B**, we use **Expected-Value Prioritisation**.  
Just like in business or finance, an engineering fix must be evaluated on three factors:
1. **Payoff:** How many failed questions will this fix realistically recover?
2. **Cost:** Will this fix make our API bill explode? (Lab 5 has a strict rule: fixes must cost $\le 2\times$ the baseline).
3. **Speed:** Will this fix add 10 seconds of lag to every customer query?

---

## 2. The Expected-Value Comparison Table

We evaluated both failure clusters side by side:

| Cluster | Failure Count ($n$) | Proposed Fix | Estimated Recovery | Cost $\Delta$ per Query | Latency $\Delta$ | Implementation Effort |
|---|:---:|---|:---:|:---:|:---:|:---:|
| **Mode 6 (Generation)** | **12** (85.7%) | **Prompt Refinement & Relax Brevity:** Remove the strict 2–3 sentence limit. Instruct the AI writer to explicitly state all secondary conditions, exception riders, and age rules using structured bullet points. | **4 to 6 questions** | $\approx +\$0.0001$ per query (a few extra output tokens) | $+150$ ms | **Low** (edit prompt in `rag.py`) |
| **Mode 4 (Ranking)** | **2** (14.3%) | **Expand Context Window (`final_k`):** Increase top-$k$ chunks from 5 to 10 to catch documents ranked #6–#10. | **0 to 1 question** (Q37 is physically missing from the corpus, so only Q35 could possibly benefit) | $+500$ input tokens ($\approx +\$0.0001$) | $+50$ ms | **Low** (change one parameter) |

---

## 3. Our One-Sentence Justification

> *"We choose **Mode 6 (Generation)** because it accounts for **85.7% of all system failures (12 out of 14)**, where the search engine already succeeded in retrieving the right documents, making prompt engineering the highest-leverage, near-zero-cost intervention."*

---

## 4. Why We Must Pre-Register Our Prediction

In science and software engineering, a **Pre-Registered Prediction** means writing down what you expect to happen **BEFORE you touch a single line of code**.

### Why is this mandatory in Lab 5?
- If you don't write down your prediction first, you fall into the trap of "hindsight storytelling"—whatever happens, you make up a convenient story claiming you expected it all along.
- By predicting in advance, you test whether your mental model of the system is actually correct.
- **You are NOT penalized if your prediction is wrong!** In fact, the course reference solution predicted a gain and measured a $-0.05$ drop, and still received full marks because they honestly reported the difference between expectation and reality.

---

## 5. Our Official Pre-Registered Prediction

> ### 📝 The Pre-Registered Prediction:
> *"By refining the generation prompt to explicitly instruct the model to include secondary clauses, age restrictions, and riders—while removing the penalizing 2–3 sentence brevity constraint—we predict that our fix will recover **4 to 6 of the 12 failures in Mode 6**, raising overall system correctness by approximately **+0.05 to +0.08 points** (from 0.800 to ~0.850–0.880)."*

---

## 6. Glossary: What Each Term Means (In Simple Plain English)

To make sure all Part B concepts are crystal clear:

- **Expected Value (Prioritisation):**  
  A rational decision formula: $\text{Expected Value} = \text{Likely Benefit} - \text{Cost} - \text{Latency Penalty}$. You choose the fix that gives the biggest net improvement per dollar and per second spent.
- **Defect Cluster:**  
  A group of failures that all share the exact same root cause (e.g., the 12 questions that all failed at the Generation stage).
- **Pre-Registered Prediction:**  
  A written commitment stating how many questions you expect to fix *before* you implement anything. It turns software tweaking into a genuine scientific experiment.
- **Recovery Estimation:**  
  An honest count of how many questions a proposed fix can realistically save, based on reading the specific failure notes rather than wishful thinking.
- **Cost Delta ($\Delta$):**  
  The change in financial cost per query caused by adding tokens or API calls. Lab 5 requires our fix to stay within $\le 2\times$ of the baseline cost.
- **Latency Delta ($\Delta$):**  
  The additional time (in milliseconds or seconds) a fix adds to query processing.
- **Single-Variable Discipline:**  
  The golden rule of engineering: change only **ONE variable at a time**. If you change both the prompt AND the retriever at once, you will never know which one actually helped or hurt.

---

## 7. Key Takeaways from Step 2

1. **Mode 6 is the clear winner:** 12 out of 14 defects are Generation errors.
2. **The fix is high-leverage and cheap:** Editing the prompt costs almost nothing and adds negligible latency.
3. **Prediction locked in:** We expect to recover **4 to 6 questions**, raising correctness by $+0.05$ to $+0.08$.
4. **Ready for Step 3:** Now we proceed to Part C to implement the fix!
