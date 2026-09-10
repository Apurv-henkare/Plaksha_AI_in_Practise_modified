# Lab 2 — Simple Explanation of the Report

> This file explains every section of `report.md` in plain English — what each table means, what the numbers are saying, and **why** the results came out the way they did.

---

## 🏢 The Setup (What We Were Doing)

An insurance company called Aurora gets thousands of support tickets every day — customers emailing about claims, billing problems, urgent situations, and so on.

We built an AI system that reads each ticket and automatically fills in a form:

| Field | What It Means |
|---|---|
| **category** | What kind of ticket? (complaint / billing / claims / technical / policy_change / information) |
| **urgency** | How urgent? (1 = not urgent at all, 5 = emergency) |
| **sentiment** | How is the customer feeling? (angry / frustrated / neutral / satisfied) |
| **product** | Which insurance plan? (gold / silver / bronze / unknown) |
| **language** | English? Hindi? Mix? (en / hi / hi-en) |
| **policy_number** | Did they mention their policy number (AUR-XXXXXXX format)? |
| **contains_pii** | Did they share private info like a phone number? |
| **escalate** | Should a human urgently review this? |

In Lab 1, we built one version of this system. In Lab 2, **we tested 7 different versions** to find out which one is the best, cheapest, and most reliable.

---

## 📊 Part B — The Grid Table (The Main Results)

This is the core of the report. We tested 7 versions ("configurations") of the system on **60 real tickets** and compared them.

### What the columns mean:

| Column | Plain English meaning |
|---|---|
| **record_acc** | How often was the AI 100% correct on every single field? (Perfect score required) |
| **field_acc** | On average, what fraction of individual fields were correct? (Partial credit) |
| **schema_valid** | Did the AI always return a properly formatted answer? (1.0 = yes, always) |
| **repair_rate** | How often did the system have to auto-fix the AI's output? |
| **cost_usd** | Total API cost to run this configuration on all 60 tickets |
| **cost_per_1k** | How much would it cost to process 1,000 tickets? |
| **p50_ms** | Typical response time (milliseconds) — what a normal ticket takes |
| **p95_ms** | Slowest 5% of responses — how bad the worst cases get |

### The results table:

| Configuration | record_acc | field_acc | schema_valid | repair_rate | cost_usd | cost_per_1k | p50_ms | p95_ms |
|---|---|---|---|---|---|---|---|---|
| zero_shot (SMALL) | 0.233 | 0.750 | 1.000 | 0.000 | $0.021 | **$0.35** | 1138 | 2010 |
| zero_shot_main (MAIN) | ❌ budget ran out | — | — | — | — | — | — | — |
| few_shot (SMALL) | 0.267 | 0.758 | 1.000 | 0.000 | $0.030 | $0.50 | 1451 | 1749 |
| few_shot_main (MAIN) | ❌ budget ran out | — | — | — | — | — | — | — |
| few_shot_reasoned (SMALL) | 0.233 | 0.763 | 1.000 | 0.000 | $0.050 | $0.83 | 1653 | 2169 |
| few_shot_reasoned_main (MAIN) | ❌ budget ran out | — | — | — | — | — | — | — |
| cascade (SMALL→MAIN) | 0.250 | 0.760 | 1.000 | 0.000 | $0.043 | $0.71 | 1130 | 22846 |

### Why did MAIN tier fail to run?

We had a budget of **$0.60** for the whole experiment. The 4 SMALL-tier runs used it all up. The MAIN (expensive) model never got a chance to process any real tickets. That's why you see "budget ran out" — not that the AI failed, but that we didn't have money left to call it. To test the MAIN model, the budget needs to be at least $2.00.

### How to read the record_acc numbers

**record_acc = 0.233** means: only 23.3% of tickets were answered with every single field correct.

That sounds terrible — but think about it: the AI has to get 8 fields right simultaneously. If it gets 7 out of 8 right, the record still counts as wrong. The **field_acc = 0.750** (75%) is more useful — it means on average, 6 out of 8 fields are correct per ticket.

### Why did all configurations score so similarly?

The differences between them (0.233 → 0.267) look small because they actually are small — and more importantly, **with only 60 test tickets, we can't reliably tell the difference**. We'd need hundreds more to be sure. The maths confirms this (see Part D below).

---

### The per-field accuracy table (zero_shot)

This shows which fields the AI struggles with most:

| Field | Accuracy | Plain English |
|---|---|---|
| **urgency** | **0.350** | ❌ Wrong 65% of the time — worst field |
| **category** | **0.483** | ❌ Wrong about half the time |
| **sentiment** | 0.667 | ⚠️ Gets it right 2 out of 3 times |
| **product** | 0.783 | ✅ Mostly correct |
| **escalate** | 0.800 | ✅ Mostly correct |
| **language** | 0.917 | ✅ Almost always correct |
| **contains_pii** | **1.000** | ✅ Perfect — never wrong |
| **policy_number** | **1.000** | ✅ Perfect — never wrong |

**Why is urgency so bad?** The AI has a strong habit of picking "2" for almost every ticket, regardless of what the real urgency should be. It avoids extremes (1 and 5). A customer at a hospital in an emergency gets urgency=4 instead of 5. A casual question gets urgency=2 instead of 1. The AI "averages" everything to the middle.

**Why are policy_number and contains_pii perfect?** These are relatively mechanical to detect — a policy number has a very specific format (AUR-XXXXXXX) and personal info like phone numbers are easy to spot. No judgment calls needed.

**Why is category at 48%?** Because there are 6 category options, and many tickets fall in grey areas. Is a customer asking about their claim settlement angry or just curious? Is a refund request "billing" or "complaint"? The AI struggles with nuance.

---

## 📌 Part A — The Six Examples (Few-Shot Selection)

We picked 6 example tickets to show the AI before asking it to classify new ones. Here's why each was chosen:

| Example ID | What It Teaches | Why an Example Works Better Than Words |
|---|---|---|
| **T0054** | "I want a refund" = complaint, not billing | The word "refund" might sound like billing, but if the customer is angry at the agent, it's a complaint. Rules in words are ambiguous. |
| **T0048** | If no "AUR-XXXXXXX" number → policy_number = null | Customers say "my policy" without giving the number. An example with null makes this concrete. |
| **T0200** | One Hindi phrase in English email = "hi-en" | You can't describe proportion in rules — one phrase is enough. An example shows this clearly. |
| **T0029** | Happy customer asking a question → urgency=1, not 3 | Just because someone is "asking" doesn't mean it's urgent. The satisfied tone overrides the question. |
| **T0238** | Support ticket ID (SR-100238) ≠ policy number | SR numbers and AUR numbers look similar. An example shows they're different things. |
| **T0021** | Hospital portal down → urgency=5 (not 3 or 4) | Multiple extreme factors together push urgency to max. Hard to describe in rules; easy to show. |

### The contamination problem — and why it matters

We had a problem: we **picked our 6 examples from the same 60 test tickets we were using to measure accuracy**.

This is called **contamination** — like a teacher who gives students the answers before the test, then tests them on the same answers.

If the AI sees "T0054 = complaint" in the examples, and then we test it on T0054 again, of course it gets T0054 right. But that's cheating — it doesn't tell us if the AI learned anything useful.

**What we did to fix it:** We excluded the 6 example tickets from the accuracy calculation. So the AI was only scored on the remaining 54 tickets it hadn't seen in the examples. This isn't a perfect fix (the ideal solution is to have a separate pool of example tickets that never appear in testing), but it avoids the worst form of contamination.

---

## 🔄 Part C — The Cascade (Two-Stage System)

### The idea

Instead of always using one AI, what if we used a smart routing system?

```
Every ticket goes to the CHEAP AI first
         │
         ├── AI seems confident AND answer looks good → ✅ Accept and move on
         │
         └── AI seems unsure OR answer has problems → 🔼 Send to EXPENSIVE AI
```

This should give us good accuracy (because hard cases get the big AI) at a lower price (because easy cases stay with the cheap AI).

### How we decided to escalate

We escalated a ticket to the expensive AI if **any** of these were true:
1. The cheap AI flagged it for human review (validation failure)
2. The AI's extracted "evidence" text was less than 10 characters (suspiciously short = low confidence)
3. We asked the cheap AI the same question **twice** (once at temperature 0, once at temperature 0.7) and it gave **different answers** — meaning it wasn't sure

> **Why different temperatures?** Temperature controls how "creative"/random the AI is. At temperature 0 it always gives the same answer. At 0.7 it introduces some randomness. If the two answers differ, the AI is genuinely uncertain. If we used temperature 0 for both, the answers would be identical every time (the cache just returns the same response), and we'd never detect disagreement — the escalation rate would be stuck at 0%.

### The cascade results

| Metric | Value | What it means |
|---|---|---|
| Escalation rate | **43.3%** (26 of 60 tickets) | Nearly half the tickets went to the expensive AI |
| Cascade cost | $0.043 · **$0.71/1k** | More than double the baseline |
| Zero_shot cost | $0.021 · **$0.35/1k** | The cheap baseline |
| Cascade accuracy | 0.250 | Barely different from 0.233 |
| Improvement | +0.017 | **Not statistically significant** |

### Why the cascade failed — the critical table

This is the most important table in the cascade section:

| | Tickets where zero_shot was WRONG | Tickets where zero_shot was RIGHT |
|---|---|---|
| **Cascade escalated** | 20 tickets (43.5%) | 6 tickets (42.9%) |
| **Cascade did NOT escalate** | 26 tickets | 8 tickets |

**Read this carefully:** The system escalated 43.5% of tickets it got wrong, and also escalated 42.9% of tickets it got right. Those are basically the **same number**.

A good escalation trigger would fire a lot more often when the AI is wrong (maybe 80% when wrong, 10% when right). Our trigger fires at the same rate regardless — meaning **it has no ability to detect actual mistakes**.

**Why?** The AI's main error is urgency bias — it consistently picks "2" for everything. That's not uncertainty, that's a bad habit. It picks urgency=2 with full confidence at both temperature 0 and temperature 0.7. The two samples agree (both say 2), so the self-consistency check thinks everything is fine — even though both answers are wrong. The escalation trigger can only detect uncertainty, not stubborn bias.

---

## 📐 Part D — Are the Differences Real? (The Statistics)

### The confidence interval table

When you only test on 60 tickets, your results have uncertainty built in. The "confidence interval" is the range of values the true accuracy might really be.

| Configuration | Measured accuracy | The true accuracy is probably between... |
|---|---|---|
| zero_shot | 0.233 | 0.144 and 0.355 |
| few_shot | 0.267 | 0.171 and 0.388 |
| few_shot_reasoned | 0.233 | 0.144 and 0.355 |
| cascade | 0.250 | 0.158 and 0.372 |

Every single range overlaps with every other range. The intervals are so wide that you can't say any configuration is better than any other just by looking at these numbers. We need a smarter test.

### The paired McNemar test — a smarter way to compare

Instead of comparing overall scores, we look at **the same 60 tickets side-by-side** for two systems:

- Count tickets where system A was right but B was wrong → call this **b**
- Count tickets where system B was right but A was wrong → call this **c**
- If B is truly better, c should be much bigger than b

The **p-value** tells you the probability that the gap between b and c is just random luck. If p < 0.05, the difference is real. If p > 0.05, it could be coincidence.

| Comparison | b (A✓ B✗) | c (B✓ A✗) | p-value | What this means |
|---|---|---|---|---|
| zero_shot vs few_shot | 3 | 5 | **0.727** | Not significant. Could easily be luck. |
| zero_shot vs few_shot_reasoned | 6 | 6 | **1.000** | Perfectly tied. Zero evidence of difference. |
| zero_shot vs cascade | 6 | 7 | **1.000** | Essentially tied. No real improvement. |

**What does p=0.727 mean in plain English?**
It means: "Even if zero_shot and few_shot were exactly the same, there's a 72.7% chance we'd see a gap this big just by random variation." That's way too likely to be coincidence. We need p < 0.05 (less than 5% chance it's luck) to claim a real difference.

**Why is the paired test better than just comparing percentages?**
Because it ignores the "easy" and "hard" tickets that both systems get right or both get wrong — it only looks at the tickets where they disagree. This removes a huge source of noise and makes small real differences detectable.

---

## 🔍 Part E — Error Analysis

### The three failure clusters

Out of 60 tickets, zero_shot got 46 wrong (at least one field incorrect). Here's where the failures came from:

**Cluster 1 — Urgency is almost always wrong (39/46 failures = 85%)**

| Problem | Example |
|---|---|
| Gold = 1 (very low), AI predicts 2 | Customer sends a casual question — AI says "medium" |
| Gold = 5 (emergency), AI predicts 4 | Hospital emergency — AI says "serious but not maximum" |
| Gold = 3, AI predicts 2 | Most gold-3 tickets are bumped down to 2 |

The AI avoids urgency 1, 3, and 5. Almost every ticket gets predicted as 2 or 4. This is a deeply embedded bias.

**Cluster 2 — "policy_change" is the AI's dustbin category (31+ cases)**

The AI doesn't know what to do with many tickets, so it dumps them into `policy_change`:

| What the ticket really was | What AI said |
|---|---|
| 11 tickets that were `information` requests | `policy_change` |
| 6 tickets that were `billing` issues | `policy_change` |
| 5 tickets that were `claims` | `policy_change` |
| 5 tickets that were `complaint` | `policy_change` |
| 4 tickets that were `technical` | `policy_change` |

**Cluster 3 — Billing, claims, and complaint get confused with each other**

These three categories look very similar to the AI:
- A customer demanding money back — is that `billing` (payment issue) or `complaint` (grievance)?  
- A customer asking about a rejected claim — is that `claims` or `complaint`?  
- All three often involve money, frustration, and formal requests

---

### The urgency confusion matrix (worst field)

This table shows every prediction the AI made for urgency, compared to what the correct answer was. Rows = what the answer should have been. Columns = what the AI predicted.

```
                       AI PREDICTED →
                  1       2       3       4       5
What it    1  |  (0)   | 10    |  2    |  (0)  |  (0)  |
really     2  |  (0)   |  9    |  3    |  3    |  1    |
should     3  |  (0)   |  6    |  (0)  |  3    |  2    |
have       4  |  (0)   |  9    |  (0)  |  (0)  |  4    |  1
been ↓     5  |  (0)   |  2    |  (0)  |  (0)  |  4    |  1
```

**Reading the matrix:**
- The top-left to bottom-right diagonal (where row = column) is where the AI is **correct**
- Everything off the diagonal is a **mistake**

**The pattern:** Column 2 is enormous. The AI predicts urgency=2 for almost everything — 36 out of 60 tickets! Gold urgency=4 tickets are mostly predicted as 2 (9 out of 14). Even gold urgency=5 (emergencies) — 2 out of 7 are called urgency=2.

**The fix is NOT more prompting.** We tried few_shot and reasoning — urgency accuracy barely moved (0.350 → 0.350 → 0.367). The bias is deeply embedded in the model's training data. The real fix would be to redesign the urgency scale, or add a post-processing calibration step.

### The category confusion matrix

```
                        AI PREDICTED →
                  billing  claims  complaint  information  policy_change  technical
What it   billing |  (0)  |  3   |   (0)   |     1      |      6       |   (0)  |
really    claims  |  (0)  |  (0) |    5    |     2      |      5       |   (0)  |
should    compl.  |  (0)  |  (0) |   (0)   |     3      |      5       |   (0)  |
have      info    |  (0)  |  (0) |   (0)   |    (0)     |     11       |   (0)  |
been ↓    pol_ch  |  (0)  |  (0) |   (0)   |     2      |      6       |    3   |
          tech    |  (0)  |  (0) |   (0)   |    (0)     |      4       |    4   |
```

**The pattern:** The `policy_change` column is the tallest — 31 tickets that were something else got labelled `policy_change`. Also notice there are **no predictions of `billing`** at all! The AI never output `billing` as a category. It treats everything billing-related as either `claims` or `policy_change`.

---

## 🏆 The Final Recommendation

**Use the simplest and cheapest option: zero_shot with the SMALL model.**

| What | Number | In plain English |
|---|---|---|
| Field accuracy | **75%** | Gets 6 out of 8 fields right per ticket on average |
| Record accuracy | **23.3%** | Fully correct on about 1 in 4 tickets |
| Cost per 1,000 tickets | **$0.35** | Thirty-five cents per thousand |
| Annual cost (10k tickets/day) | **~$1,272** | Just over $1,200 per year |
| Typical response time | **1.1 seconds** | Under 2 seconds for 95% of tickets |

**Why not the other options?**

| Alternative | Extra cost vs baseline | Accuracy gain | Worth it? |
|---|---|---|---|
| few_shot | +43% more expensive | +3.4% but p=0.727 (not real) | ❌ No |
| few_shot_reasoned | +137% more expensive | Same as baseline, p=1.00 | ❌ No |
| cascade | +103% more expensive | +1.7% but p=1.00 (not real) | ❌ No |
| MAIN model | Unknown (budget ran out) | Unknown | ⚠️ Need to test |

**When would this recommendation change?**  
If we re-ran the MAIN-tier model with a $2.00 budget and the paired test showed p < 0.05 (real improvement), we'd reconsider. The course reference says even the MAIN model only achieved p=0.71 — but we haven't confirmed that ourselves yet.

---

## ❌ The Negative Results (What Didn't Work and Why)

### 1. Few-shot examples bought nothing — WHY?

Adding 6 carefully chosen examples improved accuracy from 23.3% → 26.7%. Sounds good. But p = 0.727 — it's noise.

**Why didn't it help?** Because the original zero-shot prompt was already very well written. It contained detailed field descriptions telling the AI exactly what each field means and what values are valid. The examples had nothing new to teach. The AI already knew the rules — the examples just repeated them in a different form.

**The lesson:** If your baseline prompt is already clear and detailed, few-shot examples are wasted tokens (and money). Examples help when the prompt is vague. When the prompt is thorough, they're expensive redundancy.

### 2. Asking the AI to "show its work" bought nothing — WHY?

Making the AI write out its reasoning first (before giving the answer) doubled the output token count: 67 tokens/ticket → 126 tokens/ticket. More tokens = more cost.

The accuracy improvement? p = 1.00. Exactly zero detectable benefit.

**Why didn't it help?** The AI is already reasoning internally — it just doesn't write it down. Making it write the reasoning out doesn't change the thinking, it just documents it. The answer comes from the same internal process either way.

**When does reasoning help?** In harder tasks where forcing explicit step-by-step thinking catches logic errors. For ticket classification — a relatively pattern-matching task — there's no chain of logical steps that needs to be made explicit.

### 3. The cascade system was useless — WHY?

The cascade was supposed to be smart: send easy cases to the cheap AI, hard cases to the expensive one.

The problem: we couldn't tell the difference between easy and hard cases. The trigger (self-consistency check) fired at 43.5% for wrong tickets and 42.9% for right tickets — essentially random.

**Why couldn't it detect errors?** The AI's main error is urgency bias — it always picks 2 regardless of context. That's not uncertainty, that's a consistent wrong habit. The self-consistency test asks "do you give the same answer twice?" — and the AI says "yes, urgency=2" twice. So the test concludes the AI is confident. It is — just confidently wrong.

**The lesson:** Self-consistency catches models that are uncertain. It doesn't catch models that are consistently biased. Know your error type before picking your detection strategy.

---

## 🔑 The Three Big Takeaways

| # | Lesson | What it means in practice |
|---|---|---|
| 1 | **Fancy ≠ better** | More examples, reasoning, and cascading all failed to beat the cheapest approach. When the baseline is good, complexity just adds cost. |
| 2 | **Always check the maths** | 23% → 27% sounds like progress. But with 60 test cases, p=0.727 proves it's noise. Never trust a small difference on a small sample. |
| 3 | **Understand your errors before building solutions** | The urgency problem is a bias, not uncertainty. A cascade detects uncertainty. You need to diagnose the error type before picking a solution. |
