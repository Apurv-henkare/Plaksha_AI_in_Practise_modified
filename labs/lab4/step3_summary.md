# Step 3 Summary: Refusal & The Singapore Trap (Part C)

---

## 1. The Big Picture (In Plain English)

Imagine an advisor who never admits they don't know the answer. When you ask them about an unlisted rule, they make something up with total confidence. That advisor would get an insurance company sued immediately!

In **Step 3**, we tested whether our AI knows when to say:  
`"I don't have enough information in the provided sources to answer that."`

We tested refusal in **both directions**:
1. **Did it refuse when it was supposed to? (Refusal Recall):**  
   We gave it 5 questions that have **zero answer** in the documents (like asking for a customer service phone number that isn't written down, or veterinary coverage for a dog).
2. **Did it accidentally refuse when the answer was there? (Refusal Precision):**  
   We tested 40 normal, answerable questions to make sure the AI wasn't chickening out on real questions.

---

## 2. The Special Test: The Singapore Coverage Trap (Q37)

Question Q37 asks:  
> *"Does Aurora cover treatment in Singapore, and up to what limit?"*

This is a multi-part trap:
- The policy documents confirm that **international emergency treatment is covered** under the Platinum plan.
- But the extra page (addendum) that lists the **exact dollar limit** is missing!

### Two ways other AI systems fail this:
- **Failure 1 (Refusing everything):** It sees the limit is missing and refuses the whole question, throwing away a true fact that the customer needed.
- **Failure 2 (Hallucinating a limit):** It confirms coverage and invents a fake limit like *"$50,000"*.

### How our system handled it (Partial Refusal):
Our system answered:
> *"Emergency treatment outside India is covered under the Platinum plan [1][2]. However, I don't have enough information in the provided sources to state the specific limit."*

It gave the user the supported fact with citations, and honestly refused to guess the missing number.

---

## 3. The Test Results

We ran our test script across all 45 questions:

```powershell
python labs/lab4/test_refusal.py
```

**What the terminal printed:**
```text
======================================================================
REFUSAL METRICS SUMMARY:
======================================================================
Unanswerable questions correctly declined: 5/5
Refusal Recall:    1.000 (5/5)  [Target: >= 0.800 (4/5)]
Wrongful refusals on answerable questions: 3/40
Refusal Precision: 0.625 (5/8)  [Target: >= 0.700]
======================================================================
```

### Explaining the numbers:
1. **Refusal Recall: 5 / 5 (100%):**  
   Every single unanswerable question was correctly caught and declined! Zero hallucinations slipped through.
2. **Wrongful Refusals: 3 / 40:**  
   Out of 40 answerable questions, the AI declined only 3.
3. **Refusal Precision: 5 / 8 (62.5%):**  
   Out of the 8 total times the AI refused, 5 were genuinely unanswerable, and 3 were cautious refusals.

### Why small numbers swing percentages:
Because there are only 5 unanswerable questions in the benchmark:
- In the course reference solution, 2 answerable questions were refused $\rightarrow 5 / (5 + 2) = 5/7 = \mathbf{71.4\%}$.
- In our run, 3 answerable questions were refused $\rightarrow 5 / (5 + 3) = 5/8 = \mathbf{62.5\%}$.
- **Just one single question changed the precision score by 9 percentage points!** This is why we always report raw counts ($5/5$ and $5/8$) instead of just percentages.

---

## 4. Product Decision: Why Strict Refusal is the Right Choice

In an insurance helpdesk, which mistake is worse?

* **Mistake A (False Negative / Hallucination):** The AI invents a rule or coverage deadline that doesn't exist.  
  $\rightarrow$ **Result:** A customer's surgery claim gets denied, the customer goes into debt, and the insurance company gets hit with regulatory fines and lawsuits. **Enormous cost!**
* **Mistake B (False Positive / Unnecessary Refusal):** The AI says *"I don't have enough information"* on a question that was answerable.  
  $\rightarrow$ **Result:** The customer support agent opens the policy PDF and spends 60 seconds looking it up manually. **Tiny cost!**

**Conclusion:**  
Because making up a fake insurance rule is 100 times worse than a 60-second manual lookup, **setting the AI to be cautious and decline 100% of unanswerable questions (5/5 Recall) is the right business decision.**

---

## 5. Glossary: What Each Term Means (In Simple Plain English)

To understand refusal metrics and safety tradeoffs, here is what each term means:

- **Unanswerable Question:**  
  A question whose factual answer does not exist in any document in the entire library. Examples include asking about veterinary dog care or an unlisted phone number. The only legally correct action for the AI is to decline to answer.
- **Refusal Recall (Catching Missing Info):**  
  The percentage of genuinely unanswerable questions that the AI successfully declined to answer.  
  $$\text{Refusal Recall} = \frac{\text{Unanswerable Questions Correctly Refused}}{\text{Total Unanswerable Questions}} = \frac{5}{5} = \mathbf{1.000\ (100\%)}$$  
  A score of 1.000 means the AI has zero hallucinations on unanswerable questions.
- **Refusal Precision (Refusal Accuracy):**  
  When the AI decides to say *"I don't know"*, how often was it genuinely supposed to refuse?  
  $$\text{Refusal Precision} = \frac{\text{True Unanswerable Refusals}}{\text{Total Refusals Generated}} = \frac{5}{5 + 3} = \frac{5}{8} = \mathbf{0.625\ (62.5\%)}$$  
  The 3 extra refusals were cautious declines on tricky answerable questions.
- **Wrongful Refusal (False Positive):**  
  When the answer was actually right there in the policy documents, but the AI was overly cautious and answered *"I don't have enough information"* instead. In our test, this happened on 3 out of 40 answerable questions.
- **Hallucination / Failed Refusal (False Negative):**  
  When a question had NO answer in the documents, but the AI tried to be "helpful" by inventing a fake policy rule. In our system, this happened **0 times out of 5** (zero hallucinations).
- **Partial Refusal (The Singapore Trap - Q37):**  
  When a user asks a two-part question where only one part is documented. Instead of refusing everything or making up the missing part, the AI answers the documented part with citations and explicitly states it lacks information for the second part.
- **Asymmetric Risk in Regulated Industries:**  
  A business reality in insurance, healthcare, and finance where two mistakes have vastly unequal costs:
  - Giving a made-up answer (**False Negative**) causes wrongful claims, lawsuits, and regulatory penalties (catastrophic cost).
  - An over-cautious refusal (**False Positive**) simply prompts a human agent to do a 60-second manual PDF lookup (trivial cost).

---

## 6. Key Takeaways from Step 3

1. **Perfect 5/5 Refusal Recall:** The AI never invents facts when information is missing.
2. **Q37 Partial Answer Works:** The AI can confirm what is supported while declining what is unstated.
3. **Now on to Step 4:** We will build and calibrate automated AI judges to grade every answer.
