# What We Did in Lab 2 — Super Simple Version

---

## Okay so first, what is this whole thing about?

Imagine you work at an insurance company. People email you all day with problems. Things like:

- "My claim got rejected, I am so angry"
- "I want to add my wife to my policy"
- "Your app is broken, I can't see my policy"
- "Can you explain how my premium works?"

Now imagine you get **10,000 of these emails every single day**. You cannot read all of them manually. So we built an **AI that reads each email and fills in a form automatically**.

The form looks like this:

| Form Question | Example Answer |
|---|---|
| What type of email is this? | complaint |
| How urgent is it? (1-5) | 4 |
| How is the customer feeling? | angry |
| Did they mention their policy number? | AUR-1234567 |
| Did they share a phone number? | yes |
| What plan do they have? | gold |
| What language did they write in? | English |

That's it. The AI reads the email and fills this form. Simple.

---

## Lab 1 vs Lab 2 — What's the difference?

**Lab 1:** We built ONE version of this AI and made it work.

**Lab 2:** We asked — *"Is this the best way? Or can we do better / cheaper?"*

So we tested **7 different versions** and compared them. Like testing 7 different methods to make tea and picking the best one.

---

## The 7 versions we tested

Think of it like hiring different types of workers:

| Version | Who it's like |
|---|---|
| **Zero-shot Small** | A smart junior employee. You give them the rules book. They figure it out. Cheap. |
| **Zero-shot Main** | A senior expert. Same rules book. More expensive. *(Ran out of money before we could test this)* |
| **Few-shot Small** | Same junior, but you first show them 6 example emails with correct answers before they start. |
| **Few-shot Main** | Same senior expert, but with 6 examples shown first. *(Ran out of money)* |
| **Few-shot + Reasoning Small** | Same junior, but you also ask them to write down their thinking before giving the answer. |
| **Few-shot + Reasoning Main** | Same senior, with examples and write-down-thinking. *(Ran out of money)* |
| **Cascade** | You start with the junior. If they seem confused, you automatically send the email to the senior. |

---

## We ran out of money halfway through 😅

We had a budget of **$0.60** to run all 7 tests on 60 emails.

The junior (Small model) tests used up the whole $0.60. The senior (Main model) tests never ran.

It's like having ₹500 for groceries and spending it all on the first 4 items — the remaining 3 never got bought.

So the results you'll see below are **only for the Small model versions**.

---

## The Big Results Table

We tested on **60 real customer emails**. Here is what we found:

| Version | Got everything right | Got most things right | Cost per 1,000 emails | Speed |
|---|---|---|---|---|
| Zero-shot Small | 23% | 75% | **$0.35** | ~1 second |
| Few-shot Small | 27% | 76% | $0.50 | ~1.5 seconds |
| Few-shot + Reasoning Small | 23% | 76% | $0.83 | ~1.7 seconds |
| Cascade (both models) | 25% | 76% | $0.71 | up to 23 seconds |

### Why does "got everything right" look so low?

**23% sounds terrible.** But here's the thing — to count as "100% correct", the AI has to get ALL 8 form fields right at the same time. Get 7 out of 8 right? Doesn't count. It's like saying you passed an exam only if you got every single question right — no partial marks.

When you give partial marks (the "got most things right" column), it's 75%. That means on average it gets **6 out of 8 fields correct** per email. That's actually pretty good.

---

## Which version won?

**The cheapest, simplest one — Zero-shot Small.**

Why? Because the other versions cost more but didn't do noticeably better.

- Few-shot costs **43% more** but improved accuracy by such a tiny amount it could just be luck
- Reasoning costs **137% more** and improved nothing
- Cascade costs **103% more** and improved nothing

---

## Okay but why didn't the fancy versions do better?

### Why didn't showing 6 examples help?

We showed the AI 6 example emails with correct answers before giving it new emails. This should help, right?

It didn't — because the original instructions we gave the AI were **already very detailed and clear**. The examples had nothing new to teach. It's like giving a student a textbook, and then also reading the textbook out loud to them. The second thing adds no new information.

We ran a **math test** to check if the improvement (23% → 27%) was real. The test said **p = 0.727**. Think of p-value like this:

> **If p is close to 0** → the improvement is real, it probably happened for a reason
> **If p is close to 1** → the improvement could just be random luck, don't trust it

0.727 is very close to 1. So the improvement from examples was almost certainly just luck, not real improvement.

---

### Why didn't "write down your thinking" help?

We asked the AI to explain its reasoning before giving the answer. Like asking a student to show their working.

The problem? It **doubled the cost** (used twice as many words, and you pay per word with AI). And the accuracy didn't change at all — p = 1.00 (literally as random as it gets).

The AI was already thinking — it just wasn't writing it down. Making it write doesn't change the thinking.

---

### Why didn't the two-stage system (cascade) help?

This was the cleverest idea. Use the cheap AI first. If it seems unsure, send to the expensive AI. Smart!

But here's the problem — **43% of emails got sent to the expensive AI**. That's almost half! The system was supposed to only send the tricky ones, not every other email.

Worse, look at this table:

| | Emails where junior AI was WRONG | Emails where junior AI was RIGHT |
|---|---|---|
| Sent to expensive AI | 20 emails (43.5%) | 6 emails (42.9%) |
| Stayed with junior | 26 emails | 8 emails |

The system sent **43.5% of wrong emails** and **42.9% of right emails** to the expensive AI. Those numbers are basically the same!

That means the "send to expensive AI" trigger was as useful as **flipping a coin**. It had no idea which emails actually needed the expensive AI. So it just doubled the cost for no real improvement.

**Why did this happen?** The junior AI's main mistake is being stubborn — it always picks urgency = 2 for everything. The trigger was designed to catch when the AI is *unsure*. But the AI isn't unsure — it's confidently wrong. You can't detect stubborn wrong answers with an "are you sure?" check.

---

## What is the AI getting wrong?

Out of 60 emails, the AI got **46 of them wrong** (at least one field incorrect). Here's where it messes up:

### Mistake 1 — It always picks urgency = 2 (85% of failures)

There's a scale from 1 (chill) to 5 (emergency). The AI basically ignores this and almost always picks **2**.

| Real urgency | What AI usually says |
|---|---|
| 1 (just asking a question) | 2 (wrong — too high) |
| 3 (annoyed, needs help soon) | 2 (wrong — too low) |
| 5 (customer at hospital right now, emergency) | 4 (wrong — too low) |

It's like a thermometer that always shows 20°C regardless of the actual temperature.

### Mistake 2 — It uses "policy_change" as a rubbish bin (31+ times)

When the AI doesn't know what category to pick, it just says **policy_change**. Even when the email is clearly about a complaint, or billing, or a technical problem.

| Real category | What AI said |
|---|---|
| "I want information about my premium" (information) | policy_change ❌ |
| "Your agent lied to me" (complaint) | policy_change ❌ |
| "My claim was rejected unfairly" (claims) | policy_change ❌ |
| "Your app is broken" (technical) | policy_change ❌ |

Think of it like a student who doesn't know the answer and just writes "C" for every multiple choice question.

### Mistake 3 — It confuses billing, claims, and complaint

These three categories look very similar:
- All involve money
- All involve unhappy customers
- All involve some kind of request

The AI gets confused between them. A customer demanding a refund after bad service — is that `billing` (they want money back) or `complaint` (they're unhappy with the company)? The AI gets this wrong a lot.

---

## The "Are you sure?" Math Check

Before saying "Version A is better than Version B", we ran a proper check.

### What is a confidence interval?

When you test on only 60 emails, your results have some "wiggle room" — the true answer might be slightly different.

| Version | Measured accuracy | True accuracy is probably between... |
|---|---|---|
| Zero-shot | 23% | 14% and 36% |
| Few-shot | 27% | 17% and 39% |
| Few-shot + Reasoning | 23% | 14% and 36% |
| Cascade | 25% | 16% and 37% |

Look at those ranges. They all overlap massively. You literally cannot tell them apart from these numbers. It's like measuring heights with a ruler that's off by 10cm — all your measurements look the same.

### The paired test (smarter check)

We looked at the same 60 emails for two versions side by side:

- How many emails did version A get right but version B got wrong? → called **b**
- How many emails did version B get right but version A got wrong? → called **c**

| Comparison | b | c | p-value | Conclusion |
|---|---|---|---|---|
| Zero-shot vs Few-shot | 3 | 5 | 0.73 | No real difference |
| Zero-shot vs Reasoning | 6 | 6 | 1.00 | Exactly tied |
| Zero-shot vs Cascade | 6 | 7 | 1.00 | No real difference |

All p-values are way above 0.05. None of the "fancy" versions are provably better. The difference is noise.

---

## The Final Answer — What Should We Use?

**Use the simple cheap version: Zero-shot Small.**

| Thing | Number | What it means |
|---|---|---|
| Accuracy (per field) | **75%** | Gets about 6 out of 8 fields right per email |
| Cost per 1,000 emails | **$0.35** | 35 cents |
| Cost per year (10,000 emails/day) | **~$1,272** | About ₹1 lakh per year |
| Time per email | **~1 second** | Fast |

Every other version costs more and doesn't reliably do better.

---

## The Three Things We Learned

### 1. Simple is often better than clever
Adding examples, making the AI explain itself, building a two-stage system — none of it helped. The simplest version won. When your starting point is already good, adding complexity just adds cost.

### 2. Small differences on small tests = noise
27% vs 23% looks like an improvement. But we tested on only 60 emails. With such a small test, even random chance can cause a 4% difference. Always check the maths before celebrating.

### 3. Know WHY the AI is failing before trying to fix it
The AI always picks urgency=2. That's not because it's confused — it's a habit. We tried fixing it with examples (didn't work) and with a two-stage system (didn't work). These fixes are designed for *uncertainty*, not *stubborn habits*. Knowing the type of failure matters more than trying random fixes.
