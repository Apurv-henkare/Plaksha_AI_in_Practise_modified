# Lab 3 Agenda & Step-by-Step Guide

**Objective:** Build and test a smart search engine for Aurora Health insurance policies so future AI assistants (Labs 4–7) can find accurate answers quickly.

---

## 30-Second Summary (What to tell your Professor)

> *"In Lab 3, we are testing different search configurations to find policy answers accurately. We are running 4 experiments:*
> 1. *Chunking: finding the best way and size to cut long documents into pieces.*
> 2. *Retrieval: comparing AI meaning search (Dense), keyword search (BM25), and a combination of both (Hybrid).*
> 3. *Reranking: testing if a second, smarter AI model improves top results and whether the extra wait time and cost are worth it.*
> 4. *Index & Metadata: testing when vector databases become faster than simple math, and using status tags (`current` vs `archived`) to filter out outdated policy rules.*
> 
> *Our goal is to reach an accuracy score (nDCG@10) of at least 0.80 while keeping search fast and cheap."*

---

## The 3-Hour Step-by-Step Schedule

### Step 0: Setup & Baseline (0:00 – 0:15)
- **Goal:** Run the existing starting-point code and write down the numbers.
- **What to do:**
  1. Open terminal and run:
     ```bash
     python labs/lab3/search.py --baseline
     ```
  2. Note down the 4 baseline scores:
     - `nDCG@10` (overall ranking quality)
     - `recall@5` (how many correct documents appear in top 5)
     - `hit_rate@1` (is the #1 result correct?)
     - `MRR` (Mean Reciprocal Rank)
- **Note:** 3 questions (Q36, Q38, Q39) have no relevant document in the corpus, so our evaluation runs on **n = 42** questions.

---

### Step 1: Part A — Chunking Sweep (0:15 – 0:55)
- **Goal:** Find the best way to slice long documents into smaller pieces ("chunks").
- **Why it matters:** If an answer gets cut in half, no search algorithm can find it.
- **What to do:**
  1. **A1 (Strategy):** Test 4 cutting methods at 800 characters:
     - `fixed`: Cuts every 800 characters blindly (even mid-word/sentence).
     - `sliding`: Cuts with overlap between chunks.
     - `recursive`: Respects paragraphs and sentences.
     - `markdown`: Splits on section headings and keeps heading path names.
  2. **A2 (Size):** Take the winning strategy and test chunk sizes: **400 vs 800 vs 1600 characters**.
     - *Concept to explain:* Bigger chunks dilute the vector meaning; smaller chunks may cut off full sentences.
  3. **A3 (Headings):** Test markdown chunking **with** and **without** the `[heading > path]` prefix.
  4. **A4 (Failure case):** Find one question that failed purely because of bad chunking.
- **Command to run:**
  ```bash
  python labs/lab3/search.py --sweep chunking
  ```

---

### Step 2: Part B — Retrieval Methods (0:55 – 1:35)
- **Goal:** Compare how we search through our best chunks.
- **What to do:**
  1. **B1:** Compare the 3 retrieval methods:
     - **Dense (AI Embeddings):** Good at matching meaning and paraphrases.
     - **BM25 (Keywords):** Good at matching exact terms/codes.
     - **Hybrid (RRF):** Combines both rankings.
  2. **B2 (Per-category breakdown):** Look at results broken down by question type using **MRR** (not `hit_rate@5` which is saturated).
     - Analyze **Q44** (policy code `AUR-HI-SIL-2026` — BM25 wins).
     - Analyze **Q41** (*"skip paying on time"* vs *"grace period"* — Dense wins).
  3. **B3 & B4:** Tune RRF parameters ($k$ values: 10, 30, 60, 100) and weights.
  4. **B5 (Surprise finding):** Notice that on this dataset, **Dense alone beats Hybrid**, because the embedding model is strong and fusing a weaker keyword retriever pulls down good results.
- **Command to run:**
  ```bash
  python labs/lab3/search.py --sweep retrieval
  ```

---

### Step 3: Part C — Reranking (1:35 – 2:10)
- **Goal:** Retrieve top 30 chunks first, then use a second, smarter model to re-order the top 5.
- **What to do:**
  1. **C1 (Cross-Encoder):** Test the `ms-marco-MiniLM-L-6-v2` local model. Check if accuracy improved and how much latency (milliseconds) was added.
  2. **C2 (LLM Reranker):** Test using an LLM to score chunks. Notice it gives high accuracy but is slow (~28 seconds) and costs money per query.
  3. **C3 (Deployment Decision):** Fill a decision table and pick two different solutions:
     - For **live user chat:** pick the fast method (e.g. Dense or fast Cross-Encoder).
     - For **nightly batch report:** pick the most accurate method even if slow (LLM reranker).
  4. **C4:** Find a question where reranking made the ranking *worse*.
- **Command to run:**
  ```bash
  python labs/lab3/search.py --sweep rerank
  ```

---

### Step 4: Part D — Vector Index & Metadata Filtering (2:10 – 2:35)
- **Goal:** Test database scalability and smart data filtering.
- **What to do:**
  1. **D1:** Compare exact NumPy matrix search vs ChromaDB (HNSW index) on our small 160-chunk corpus. (NumPy is actually faster here!).
  2. **D2:** Test search speed on larger corpus sizes (~160, ~4,000, and ~40,000 chunks) to see at what point a vector database becomes faster.
  3. **D3 (The Metadata Trap):** Questions Q29, Q30, and Q31 fail because an outdated 2024 policy document (`claims-timelines-2024-ARCHIVED`) gives the wrong answer.
     - Solution: Tag documents as `status: current` or `archived`. Filter out archived documents at search time.
     - Result: Instant 100% accuracy on those questions without changing any AI model!
- **Command to run:**
  ```bash
  python labs/lab3/search.py --sweep index
  ```

---

### Step 5: Deliverables & Show & Tell (2:35 – 3:00)
1. **Code:** `labs/lab3/search.py` with all 4 sweep functions filled in.
2. **Data:** `reports/lab3_sweeps.json` containing recorded metrics.
3. **Report:** `report.md` summarizing the findings, charts, and deployment decisions.
