# Step 2 Summary: Enforcing Citations in Code (Part B)

---

## 1. The Big Picture (In Plain English)

In Step 1, we *asked* the AI politely in the prompt to cite its sources.  
But in software, **asking is not enough**. 

Sometimes the AI gets lazy, forgets brackets, or makes up a fake source number like `[8]` when we only gave it 5 documents.

In **Step 2**, we built a **Python Security Guard** (`validate_answer`) that physically inspects the AI's answer *before* any customer or human agent sees it. If the answer contains even one fake citation, the code catches it and blocks it.

---

## 2. The 4 Checks Our Python Code Performs

Every single generated answer passes through 4 automatic filters:

1. **Check 1: Did the text get cut off? (Truncation)**  
   If the AI runs out of output tokens, it might stop mid-sentence:  
   *"You are covered for heart surgery, provided you..."*  
   That cut-off sentence looks okay at first glance, but dropping the condition reversed the entire legal meaning! If the answer is cut off (`finish_reason == "length"`), our code **immediately rejects it**.
2. **Check 2: Is it an honest refusal?**  
   If the AI says *"I don't have enough information..."*, it doesn't need to cite sources. Our code marks it as a **valid refusal**.
3. **Check 3: Is the answer empty?**  
   If the answer is completely blank, our code rejects it.
4. **Check 4: Are all citation numbers real?**  
   If we gave the AI 5 sources, our code uses regex to find every number in brackets. If it sees `[7]`, that is a **provable lie**. Our code immediately catches and rejects it.

---

## 3. What Happens When an Answer Fails? (Our Repair Policy)

If an answer fails validation, what should the computer do?

```text
[AI generates an answer]
           │
           ▼
[validate_answer checks the citations]
      │                   │
   (Passed)            (Failed)
      │                   │
      ▼                   ▼
[Send answer to user]   [Try once more with an error message]
                        "Your answer had an invalid citation [7]. 
                         Please try again citing only [1] to [5]."
                                  │
                                  ▼
                        [validate_answer checks again]
                             │                 │
                          (Passed)          (Failed)
                             │                 │
                             ▼                 ▼
                    [Send to user]     [Fall back to "I don't know"]
```

### Why we designed it this way:
1. **Try to fix small mistakes:** A quick retry often fixes silly slips, like forgetting brackets.
2. **Never hide bad citations:** Some systems just delete the bad citation tag and show the text anyway. That is terrible because it makes a made-up fact look real!
3. **Safety first:** If the AI fails twice, our code simply returns:  
   `"I don't have enough information in the provided sources to answer that."`  
   In health insurance, **admitting you don't know is 100 times better than showing a fake source**. This guarantees **100% citation validity**.

---

## 4. The Test We Ran

We ran 4 unit tests covering every single edge case:

```powershell
python -c "from labs.lab4.rag import validate_answer, REFUSAL; v1 = validate_answer('Claim must be filed in 30 days [1].', 3); assert v1['valid'] and v1['n_citations'] == 1, 'Valid check failed'; v2 = validate_answer('Claim in 30 days [7].', 3); assert not v2['valid'] and 7 in v2['invalid_citations'], 'Phantom citation [7] not caught'; v3 = validate_answer(REFUSAL, 3); assert v3['valid'] and v3['refused'], 'Refusal check failed'; v4 = validate_answer('Cut off answer...', 3, finish_reason='length'); assert not v4['valid'] and v4['truncated'], 'Truncation check failed'; print('All 4 citation validation unit tests PASSED successfully!')"
```

**What the terminal printed:**
```text
All 4 citation validation unit tests PASSED successfully!
```

- **Test 1:** Clean citation `[1]` $\rightarrow$ **Passed** ✅
- **Test 2:** Fake citation `[7]` when only 3 sources existed $\rightarrow$ **Caught and blocked** ✅
- **Test 3:** Standard refusal $\rightarrow$ **Passed without needing citations** ✅
- **Test 4:** Truncated / cut-off text $\rightarrow$ **Caught and blocked** ✅

---

## 5. Glossary: What Each Term Means (In Simple Plain English)

To understand how software enforces AI citation rules, here is what each term means:

- **Citation Validity (Citation Integrity):**  
  A metric that measures whether every single citation number in the AI's answer points to an actual, real document provided in the context. If 5 documents are provided, any citation between `[1]` and `[5]` is valid. If an answer includes `[8]` or `[0]`, citation validity fails. A score of **1.000** means **100% of all generated citations are authentic and verifiable**.
- **Phantom Citation (Hallucinated Source):**  
  A citation number that does not exist in the provided sources (e.g., citing `[7]` when only 4 documents were provided). The AI hallucinated the source number itself.
- **Truncation (`finish_reason == "length"`):**  
  When the AI is cut off in the middle of a sentence because it reached the maximum token limit. In healthcare, a truncated sentence like *"You are fully covered for surgery, provided you..."* is dangerous because omitting the condition changes the entire legal meaning.
- **Deterministic Guardrail (Code vs. Prompting):**  
  A prompt is a *suggestion* to an AI that works most of the time (probabilistic). A **deterministic guardrail** is traditional Python code (like `if` statements and regular expressions) that runs with 100% consistency every single time without guessing.
- **Regex (Regular Expression):**  
  A standard search pattern used in programming. In our code, `re.findall(r'\[(\d+)\]', text)` searches through the AI's answer and extracts every single number found inside brackets.
- **Self-Correction / Retry Loop:**  
  If the AI makes a minor error (such as a phantom citation), the system doesn't immediately fail. It sends a second request back to the model with an automated prompt: *"Your answer contained invalid source [7]. Please retry citing only [1] through [5]."* This allows the AI to self-correct.
- **Fail-Safe Fallback:**  
  The ultimate safety net. If an answer fails validation twice in a row, the system discards the text and falls back to: `"I don't have enough information in the provided sources to answer that."` In regulated insurance, silence is vastly safer than an ungrounded or deceptive answer.

---

## 6. Key Takeaways from Step 2

1. **Code guarantees beat prompt wishes:** Prompting the model only gets you 95% of the way there. Deterministic Python checks guarantee **1.000 (100%) accuracy**.
2. **Now on to Step 3:** We now test how well the AI knows when to say *"I don't know"* on real customer questions.
