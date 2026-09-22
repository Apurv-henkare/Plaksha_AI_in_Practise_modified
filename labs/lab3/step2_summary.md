# Step 2 Summary & Revision Guide: Search Methods (Part B)

---

## 0. The Big Picture: Why Step 2 Exists & How It Connects to Step 1

> **The Question:** *"We already retrieved documents in Step 1. Why are we retrieving documents again in Step 2?"*

In any rigorous engineering experiment, you must follow the **Scientific Method: change only ONE variable at a time**:

| Experiment Phase | What Was Changed (The Variable) | What Was Kept Constant (The Fixed Ruler) | The Winning Decision |
|---|---|---|---|
| **Step 1 (The Data)** | **The Chunking:** Cutting styles (`fixed`, `sliding`, `recursive`, `markdown`) and sizes (400, 800, 1600). | **Dense Search Engine** was kept constant on every run. | **`markdown-400`** won by +5 points. |
| **Step 2 (The Search Engine)** | **The Search Algorithm:** `Dense` (meaning) vs `BM25` (keywords) vs `Hybrid` (RRF combination). | **`markdown-400` chunks** were frozen and kept constant. | **`Dense`** won by +5.8 points over Hybrid! |
| **Step 3 (The Inspector)** | **Two-Stage Reranking:** Fast wide search ($k=30$) followed by Cross-Encoder / LLM re-scoring. | Best Chunks (`markdown-400`) + Best Retriever (`Dense`). | *Coming up next!* |

### What Step 2 is Doing:
In Step 1, we finished creating our **235 neat, atomic index cards** (`markdown-400`). 
In **Step 2**, the index cards stay completely untouched. Instead, we tested **which search engine** is best at searching through those 235 cards to answer customer questions.

---

> **In 2 Sentences:**
> In Step 1, we found the best way to cut our policy documents into chunks (`markdown-400`). In Step 2, we tested three different search engines—**Dense (AI Meaning)**, **BM25 (Exact Keywords)**, and **Hybrid (Combining Both)**—to discover which one finds policy answers most accurately.

---

## 1. How Each Search Engine Works (In Simple English)

Before looking at the numbers, let's understand how these three search technologies actually work under the hood:

### 1. Dense Search (Concept / Meaning Search)
- **How it works:** An AI embedding model reads the customer's question and turns it into a list of 768 numbers (a mathematical vector) representing its **meaning**. It does the same for every policy chunk. Then, it measures the angle between vectors (cosine similarity).
- **Its superpower:** It understands **synonyms and paraphrasing**.
  - If a customer asks: *"If I skip paying, when do I lose my benefits?"*
  - And the policy says: *"Grace period is 30 days before policy lapses."*
  - Dense search knows that "skip paying" means "grace period" and "lose benefits" means "policy lapse", even though **not a single word is the same**!

---

### 2. BM25 Search (Keyword / Word Counter Search)
- **How it works:** BM25 is an advanced keyword search engine (the same technology powering Wikipedia and ElasticSearch). It looks for exact word matches using two rules:
  1. **Term Frequency (TF):** How many times does the searched word appear in the chunk? (More times = higher score).
  2. **Inverse Document Frequency (IDF):** How rare is this word across the whole library? Common words like "insurance", "hospital", or "patient" get low scores. Rare words like `AUR-HI-SIL-2026` or "Laparoscopic" get massive scores!
- **Its superpower:** Exact codes, product names, numbers, and rare words.
- **Its fatal weakness:** If the user uses different words than the document, BM25 gets a score of **zero**.

---

### 3. Hybrid Search & How RRF Works

#### The Problem: Why can't we just add Dense scores and BM25 scores together?
- Dense scores are cosine similarities that live between **0.0 and 1.0** (e.g. `0.82`).
- BM25 scores are open-ended numbers that can be anything from **0 to 50+** (e.g. `18.4`).
- Adding them directly is like adding 5 kilometers to 20 kilograms—it makes no mathematical sense!

#### The Solution: Reciprocal Rank Fusion (RRF)
Instead of adding their raw scores, Hybrid uses **RRF**, which looks only at the **rank positions** (1st place, 2nd place, 3rd place). 

Here is the exact formula:
$$\text{RRF Score} = \sum \frac{\text{Weight}}{k + \text{Rank}}$$

---

### What is "$k$" in Hybrid RRF? (The Top-Rank Damper)
Look closely at the bottom of the fraction: $(k + \text{Rank})$.
- **Why do we need $k$?** 
  If $k$ did not exist (or was 0), Rank 1 would get $\frac{1}{1} = 1.0$, while Rank 2 would get $\frac{1}{2} = 0.5$. Rank 1 would be **twice as powerful** as Rank 2! A single retriever that randomly put a wrong document at #1 would completely bully and overpower the other retriever.
- **How $k=60$ fixes this:**
  By adding a constant like $k=60$:
  - Rank 1 gets: $\frac{1}{60 + 1} = \frac{1}{61} \approx 0.01639$
  - Rank 2 gets: $\frac{1}{60 + 2} = \frac{1}{62} \approx 0.01613$
  - Rank 3 gets: $\frac{1}{60 + 3} = \frac{1}{63} \approx 0.01587$
- **In plain English:** $k$ acts like a **gentle shock absorber**. It smooths out the top ranks so that one retriever cannot aggressively override the other.

---

### What are Fusion Weights? ($w_{\text{dense}} : w_{\text{bm25}}$)
- By default ($1.0 : 1.0$), Dense and BM25 have equal voting power (50/50).
- If we set weights to ($2.0 : 1.0$), Dense gets **two votes** for every **one vote** BM25 gets.

---

## 2. Experiment B1: The Main Contest (Dense vs BM25 vs Hybrid)

We ran all 42 benchmark questions through all three search engines on our best chunks (`markdown-400`):

| Search Engine | First Result (`hit_rate@1`) | Top 5 (`hit_rate@5`) | Coverage (`recall@5`) | Rank Score (`mrr`) | Overall Score (`ndcg@10`) | Speed (p95 Latency) |
|---|---|---|---|---|---|---|
| **`dense`** | **78.57%** | **97.62%** | **90.28%** | **0.8800** | **0.8527** 🏆 | 6.26 ms |
| **`bm25`** | 47.62% | 92.86% | 79.56% | 0.6698 | **0.6978** | **0.96 ms** |
| **`hybrid (k=60)`** | 66.67% | 97.62% | 86.31% | 0.7976 | **0.7949** | 2.46 ms |

---

### Detailed Observations for Each Search Engine in B1:

#### 1. `dense` (The Clear Winner — Score: 0.8527)
- **Observation:** Dense won by a landslide across all quality metrics. It placed the correct document at Rank #1 in **78.6% of questions** and achieved an overall grade of **0.8527**.
- **Why It Won:** Customer insurance questions are full of natural, messy human language (*"Can I claim for IVF?"*, *"How much do I pay out of pocket?"*). Dense understands the underlying concept and matches it to formal insurance definitions (*"exclusions"*, *"co-payment"*).

#### 2. `bm25` (The Lexical Baseline — Score: 0.6978)
- **Observation:** BM25 performed poorly. It was **15.5 points lower than Dense** in `ndcg@10` (0.6978 vs 0.8527) and got the #1 rank right less than half the time (**47.6%**).
- **Why It Struggled:** Customers rarely use the exact legal words written in policy contracts. When the words don't match, BM25 returns nothing. Furthermore, distractor documents in our library (like travel or car insurance) repeat words like "claim" and "hospital", confusing BM25's word counter.
- **Its Only Advantage:** It is extremely fast (under 1 millisecond).

#### 3. `hybrid (k=60)` (The Big Surprise of Lab 3 — Score: 0.7949)
- **Observation:** **Hybrid search was nearly 6 points WORSE than pure Dense** (0.7949 vs 0.8527), and its #1 accuracy dropped by **-11.9%** (from 78.6% down to 66.7%)!
- **Why Did Hybrid Lose? (The Core Lesson):**
  Textbooks often claim *"Hybrid search is always best"*. But RRF is a blind voting system: **it forces BM25's opinion into every single query**, even when BM25 is completely clueless! Because BM25 was so much weaker than Dense on this dataset, it dragged down good Dense rankings far more often than it helped.

---

## 3. Experiment B2: Deep Dive by Question Type (Why Hybrid Lost)

To see the exact reason why Dense beat Hybrid, we looked at how each search engine performed on different question categories using **MRR** (Rank Quality):

### Category Breakdown Table (MRR per Category):
| Question Category | Question Count ($n$) | Dense MRR | BM25 MRR | Hybrid MRR | Who Won? |
|---|---|---|---|---|---|
| **`multi_hop`** (Complex, multi-part rules) | 10 | **1.0000** | 0.6500 | 0.8167 | **Dense wins easily** |
| **`paraphrase`** (Different wording) | 5 | **0.8000** | 0.4867 | 0.6500 | **Dense wins easily** |
| **`aggregation`** (Combining limits) | 4 | **0.8750** | 0.3750 | 0.5833 | **Dense wins easily** |
| **`trap_archived`** (Outdated 2024 files) | 3 | **0.8333** | 0.5111 | 0.6667 | **Dense wins easily** |
| **`single_hop`** (Direct fact lookup) | 18 | 0.9074 | 0.8519 | **0.9444** | Hybrid slight edge |
| **`unanswerable`** (No answer exists) | 2 | 0.3125 | **0.4167** | 0.3750 | BM25 slight edge |

### The Head-to-Head Tally:
$$\text{Dense won on } \mathbf{20} \text{ questions} \quad\Big|\quad \text{BM25 won on only } \mathbf{6} \text{ questions} \quad\Big|\quad \text{Ties: } 16$$
Dense beat BM25 on **more than 3× as many questions**!

---

### Two Questions That Explain the Whole Mechanism:

#### Story 1: Question Q44 — An Exact Policy Code (Where BM25 Rescues Dense)
- **Question:** *"AUR-HI-SIL-2026 — what are the sum insured options?"*
- **What happened:**
  - **Dense MRR:** `0.5000` (Rank 2) — AI embedding models break unfamiliar codes like `AUR-HI-SIL-2026` into random pieces. Dense was not 100% sure which policy it was.
  - **BM25 MRR:** `1.0000` (Rank 1!) — BM25 saw `AUR-HI-SIL-2026` as a rare token that appears in only one file. It immediately put it at #1.
  - **Hybrid MRR:** `1.0000` (Rank 1!) — **Hybrid worked as advertised here!** It combined BM25's keyword signal to rescue the query from Rank 2 up to Rank 1.

#### Story 2: Question Q41 — Pure Human Paraphrase (Where BM25 Destroys Dense)
- **Question:** *"If I skip paying on time, how long before I lose everything I've built up?"*
- **Correct Document:** `grace-period.md`
- **What happened:**
  - The customer used natural, emotional words (*"skip paying on time"*, *"lose everything"*).
  - The document used dry legal words (*"grace period"*, *"policy lapse"*).
  - **Dense MRR:** `1.0000` (Rank 1!) — Dense understood the concept instantly and gave it #1.
  - **BM25 MRR:** `0.0000` (Failed completely!) — Because zero words matched, BM25 scored it 0.
  - **Hybrid MRR:** `0.2500` (Rank 4 — **A Disaster!**)
  - **Why did Hybrid fail here?** Because BM25 gave a terrible ranking, the RRF voting formula **dragged the perfect Rank 1 answer down to Rank 4**! 

> **Summary of the Trade-off:**
> Hybrid rescued 1 question (Q44), but damaged multiple questions like Q41. In the real world, customers ask far more paraphrase questions than exact product codes, which is why Hybrid lost overall.

---

## 4. Experiment B3: What Happens When We Tune $k$? ($k=10, 30, 60, 100$)

We tested different values for the smoothing constant $k$ in RRF:

| RRF Value | First Result (`hit_rate@1`) | Top 5 (`hit_rate@5`) | Coverage (`recall@5`) | Rank Score (`mrr`) | Overall Score (`ndcg@10`) | Latency p95 |
|---|---|---|---|---|---|---|
| **`k = 10`** | 66.67% | **100.00%** | **88.49%** | **0.8115** | **0.8156** | 2.81 ms |
| **`k = 30`** | 66.67% | 97.62% | 86.31% | 0.7976 | 0.7949 | 2.40 ms |
| **`k = 60`** *(default)* | 66.67% | 97.62% | 86.31% | 0.7976 | 0.7949 | 2.47 ms |
| **`k = 100`** | 66.67% | 97.62% | 86.31% | 0.7976 | 0.7901 | 2.51 ms |

---

### Observations on Tuning $k$:

1. **Why `k=10` scored slightly higher (0.8156):**
   - A smaller $k$ gives slightly more weight to the absolute top ranks. Because it rewarded true Rank 1 matches a little more, `ndcg@10` rose slightly from 0.7949 to 0.8156.
2. **Why `k=30`, `k=60`, and `k=100` are almost identical (0.7949 to 0.7901):**
   - The scores are almost flat. This is known as **RRF Insensitivity**.
   - **Why this is usually a good thing:** In production, engineers love algorithms that don't break when hyperparameters change. You don't have to waste time fine-tuning $k$.
3. **The Big Takeaway:**
   - Even at its best tuning ($k=10$, score 0.8156), **Hybrid still cannot beat pure Dense (0.8527)**. Tuning $k$ cannot fix the fact that BM25 is giving unhelpful recommendations.

---

## 5. Experiment B4: What Happens When We Give Dense More Votes? (Weights)

Next, we tested giving unequal weights to Dense vs BM25:

| Weight Ratio (Dense : BM25) | Meaning in Plain English | First Result (`hit_rate@1`) | Coverage (`recall@5`) | Overall Score (`ndcg@10`) |
|---|---|---|---|---|
| **`1.0 : 1.0`** | Equal 50/50 vote | 66.67% | 86.31% | 0.7949 |
| **`2.0 : 1.0`** | Dense gets 2 votes, BM25 gets 1 | 69.05% | 87.50% | 0.8068 |
| **`3.0 : 1.0`** | Dense gets 3 votes, BM25 gets 1 | 69.05% | **89.29%** | **0.8136** 📈 |
| **`1.0 : 2.0`** | BM25 gets 2 votes, Dense gets 1 | **71.43%** | 85.52% | 0.7926 📉 |

---

### Observations on Weights:

1. **Giving Dense more weight improves the score:**
   - As we increased Dense's voting power from 1.0 $\rightarrow$ 2.0 $\rightarrow$ 3.0, overall quality steadily climbed from **0.7949 $\rightarrow$ 0.8068 $\rightarrow$ 0.8136**.
   - **Why:** The more you trust Dense and silence BM25, the fewer mistakes BM25 can introduce!
   - In fact, if you increased Dense's weight to 100:1, you would eventually reach **0.8527** (pure Dense).
2. **Giving BM25 more weight hurts overall quality:**
   - At `1.0 : 2.0`, overall score dropped to **0.7926** because BM25's errors were magnified.

---

## 6. Key Findings & Final Presentation Takeaways

When presenting Step 2 to your professor or evaluators, highlight these core conclusions:

1. **Published Best Practice is a Prior, Not a Guarantee:**
   - Most textbooks say: *"Always use Hybrid search"*. On our dataset, **pure Dense (0.8527) beat Hybrid (0.7949) by 5.8 points**.
   - **The Lesson:** Always measure on your own data. Never adopt an architecture just because a blog post recommended it.
2. **Why Dense Won:**
   - Modern embedding models are powerful enough to capture both vocabulary and semantics. Dense beat BM25 on **20 out of 26 non-tied questions (77% win rate)**.
3. **The Q44 vs Q41 Mechanism:**
   - BM25 is great at rare exact identifiers like `AUR-HI-SIL-2026` (Q44).
   - But BM25 completely fails on human paraphrases like *"skip paying on time"* (Q41), dragging Rank 1 down to Rank 4 in Hybrid fusion.
4. **Final Recommendation for Step 2:**
   - We select **`DenseRetriever` on `markdown-400` chunks** as our search champion.
   - We now advance to **Step 3 (Part C: Reranking)** to see if a second-stage Cross-Encoder or LLM can make search even more accurate!
