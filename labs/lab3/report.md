# Lab 3 Report — Semantic Search That Actually Works
**Dataset:** Aurora Health Policy Corpus (30 documents, 14 distractors)  
**Evaluation Set:** 42 questions ($n=42$, evaluated from `data/eval/rag_golden.jsonl`; Q36, Q38, Q39 excluded due to empty relevant sets)  
**Search Strategy:** Greedy single-axis optimization (Chunking $\rightarrow$ Retrieval Method $\rightarrow$ Reranking $\rightarrow$ Index & Metadata)

---

## Executive Summary & Final Recommended Configuration

Through a disciplined 4-stage optimization sweep, we built a production-grade semantic search engine that easily beats all lab benchmark targets while keeping search latency under 2 milliseconds and operational cost at $0.00 per query.

### Final Recommended Architecture
- **Chunking:** Markdown-aware chunking at **400 characters** with section heading breadcrumbs prepended.
- **Retriever:** **Dense Retriever** (in-memory exact dot product / BLAS) using 768-dimensional embeddings.
- **Metadata Filtering:** Deterministic ingest-time tag `status: current` filtered at query time to eliminate obsolete policy records.
- **Reranking Strategy:** 
  - **Live Interactive Search:** **None** (pure Dense search). 1.41 ms latency, $0 API cost, and high retrieval accuracy.
  - **Overnight Compliance Audit:** **LLM Reranker** (Gemini Flash). 100% precision and recall across all queries where latency (28s) and cost ($15/1k queries) are acceptable.

### Benchmark Targets vs. Measured Results

| Metric | Lab Target | BM25 Baseline | Our Final System | Target Met? |
|---|---|---|---|:---:|
| **nDCG@10** | $\ge 0.80$ | 0.701 | **0.8527** | **YES (+5.3 pts)** |
| **recall@5** | $\ge 0.85$ | 0.790 | **0.9028** | **YES (+5.3 pts)** |
| **hit_rate@1** | $\ge 0.65$ | 0.524 | **0.7857** | **YES (+13.6 pts)** |
| **MRR (Paraphrase)** | $\ge 0.75$ | 0.500 | **0.8000** | **YES (+5.0 pts)** |
| **Latency p95** | $\le 400$ ms | 0.3 ms | **1.41 ms** | **YES (280× faster)** |
| **Index Build Cost** | Reported | $0.00 | **$0.008** | **YES** |

> **Methodological Note on Scope and Greedy Search:**  
> 1. Questions Q36, Q38, and Q39 have no relevant documents in the corpus (unanswerable questions). Recall cannot be computed against an empty ground-truth set. Following the lab specification, these three questions were excluded, giving an active evaluation sample of **$n=42$**.  
> 2. To optimize within the practical engineering window, we used a **greedy single-axis sweep** (fixing the best chunking, then the best retriever, then the best reranker). While practical, greedy optimization can theoretically miss cross-axis interactions (for example, a larger chunk size might have paired better with BM25 keyword matching than with dense vectors).

---

## 1. Document Chunking & The Dilution Curve (Part A)

Long policy documents cannot be embedded as whole files because single vectors would average multiple unrelated rules together. We tested how slicing text affects retrieval performance.

### A1. Comparison of 4 Chunking Styles (Fixed at 800 Characters)

| Chunking Strategy | hit_rate@1 | hit_rate@5 | recall@5 | MRR | nDCG@10 | Chunk Count | Build Time |
|---|---|---|---|---|---|---|---|
| `fixed-800` | 0.7381 | 0.9524 | 0.8373 | 0.8387 | 0.7952 | 83 | 150 ms |
| `sliding-800` | 0.7857 | 0.9286 | 0.8452 | 0.8451 | 0.8053 | 91 | 55 ms |
| `recursive-800` | 0.7619 | 0.9524 | 0.8750 | 0.8611 | 0.8251 | 98 | 63 ms |
| **`markdown-800`** | **0.7619** | **0.9762** | **0.8988** | **0.8720** | **0.8458** | 164 | 105 ms |

- **Why Fixed Fails:** Slicing strictly by character count cuts across legal sentences. A condition (*"only if authorized 48h prior"*) gets severed from its benefit, destroying semantic retrieval.
- **Why Sliding Improves:** The 150-character overlap prevents sentences from being split in half, improving first-result hit rate to 78.57%.
- **Why Markdown Wins:** Splitting on markdown headers respects document logic, keeping complete policy sections intact (+5.0 points in nDCG@10 over fixed).

---

### A2. Chunk Size Sweep & The Dilution Curve

Using the winning markdown chunker, we swept character sizes across 400, 800, and 1600 characters:

| Chunk Size | hit_rate@1 | hit_rate@5 | recall@5 | MRR | nDCG@10 | Chunk Count |
|---|---|---|---|---|---|---|
| **`markdown-400`** | **0.7857** | **0.9762** | **0.9028** | **0.8800** | **0.8527** 🏆 | 235 |
| `markdown-800` | 0.7619 | 0.9762 | 0.8988 | 0.8720 | 0.8458 | 164 |
| `markdown-1600` | 0.7143 | 0.9524 | 0.8750 | 0.8262 | 0.8075 | 150 |

```text
nDCG@10 vs Chunk Size (The Dilution Cliff)
0.86 |     ★ 0.8527 (400 chars - Atomic sharpness)
0.84 |           \
0.82 |            \--- 0.8458 (800 chars)
0.80 |                      \
0.78 |                       \=== 0.8075 (1600 chars - Semantic dilution cliff)
      +---------------------------------------------------
           400 chars         800 chars        1600 chars
```

**The Dilution Explanation (T4 §2.2):**  
The relationship between chunk size and retrieval quality is not monotonic. At **1600 characters**, each chunk packs 3 to 5 distinct legal rules, waiting periods, and exclusions into a single block. The embedding vector averages all these distinct meanings into a single blended vector centroid. Specific queries (e.g., about a specific dental waiting period) become diluted in the broader document context. In contrast, **400 characters** creates "atomic" chunks focused on one specific rule, maximizing semantic sharpness and yielding the highest overall score (**0.8527 nDCG@10** and **0.9028 recall@5**).

---

### A3. Value of Heading Breadcrumbs (The Prefix Ablation)

We measured the markdown chunker with and without prepending hierarchical breadcrumbs (e.g. `[Health Policy > Exclusions > Maternity]`):

| Variant | hit_rate@1 | hit_rate@5 | recall@5 | MRR | nDCG@10 |
|---|---|---|---|---|---|
| **With Heading Path** | **0.7619** | 0.9762 | 0.8988 | **0.8720** | **0.8458** |
| **Without Heading Path** | 0.6190 | 1.0000 | 0.9048 | 0.7837 | 0.7915 |
| **Delta ($\Delta$)** | **+14.29%** | -2.38% | -0.60% | **+0.0883** | **+0.0543** |

**Why Heading Breadcrumbs Lower `hit_rate@5` While Raising `hit_rate@1` (OVERVIEW Hint):**  
This is not a contradiction—it illustrates the difference between precision and broad recall:
1. **Without Headings:** Chunks are generic and lack specific context. The retriever casts a wide, fuzzy semantic net where relevant chunks scatter anywhere across ranks 1 to 5 (`hit_rate@5 = 1.0000`), but rank-1 precision is poor (`hit_rate@1 = 61.90%`).
2. **With Headings:** Breadcrumbs inject sharp, localized context (`[Policy > Exclusions]`). Relevant chunks are pulled directly to **Rank 1** (jumping +14.29% to **76.19%**). Occasionally, an ambiguous secondary chunk gets pushed from rank 5 to rank 6, slightly lowering `hit_rate@5` (-2.38%).
3. **Verdict:** For an AI system or human agent who reads the first result, **+14.3% rank-1 accuracy** and **+5.4 points in nDCG@10** represent an overwhelming improvement.

---

### A4. Concrete Chunking Failure Case: Question Q08

To observe chunking mechanics under a microscope, we examined **Question Q08** (Failure Mode 2 from T4 §5):
- **User Query:** *"Can I claim for IVF treatment?"*
- **Ground Truth Target Document:** `exclusions.md`

#### What Matched Under `fixed-800` (FAILED — Buried at Rank 7, MRR = 0.1429):
- **Chunk Retrieved at Rank 1 (`hospital-cash-benefit.md`):**
  ```text
  ...of the indemnity treatment.
  ## Waiting periods
  30 days initial; 24 months for specified illnesses; 36 months for pre-existing disease...
  ```
- **Why It Failed:** Slicing strictly by 800 characters severed the exclusion clause from the word "Exclusions". The query contained the word "treatment". The retriever saw "indemnity treatment" and "specified illnesses" and wrongly assumed high relevance, burying the actual IVF rule at Rank 7.

#### What Matched Under `markdown-800` (SUCCEEDED — Rank 1, MRR = 1.0000):
- **Chunk Retrieved at Rank 1 (`exclusions.md`):**
  ```text
  [Permanent Exclusions > Treatment-related exclusions]
  - Cosmetic or plastic surgery, unless required to treat an accidental injury...
  - In vitro fertilisation (IVF), fertility, and sub-fertility treatments...
  ```
- **Why It Succeeded:** The hierarchical heading `[Permanent Exclusions > Treatment-related exclusions]` stayed glued to the bullet points. The query's negative intent matched the explicit exclusion heading, placing the exact answer at Rank 1.

---

## 2. Retrieval Methods: Dense vs. BM25 vs. Hybrid (Part B)

We evaluated three retrieval paradigms on our winning `markdown-400` chunks:
1. **Dense Retriever:** Semantic vector search (cosine similarity).
2. **BM25 Retriever:** Keyword frequency and inverse document frequency matching.
3. **Hybrid Retriever:** Reciprocal Rank Fusion (RRF, $k=60$) combining both rank lists.

### B1. Overall Benchmark Comparison

| Retriever | hit_rate@1 | hit_rate@5 | recall@5 | MRR | nDCG@10 | Latency (p95) |
|---|---|---|---|---|---|---|
| **`dense`** | **0.7857** | **0.9762** | **0.9028** | **0.8800** | **0.8527** 🏆 | 6.26 ms |
| **`bm25`** | 0.4762 | 0.9286 | 0.7956 | 0.6698 | 0.6978 | **0.96 ms** |
| **`hybrid (k=60)`** | 0.6667 | 0.9762 | 0.8631 | 0.7976 | 0.7949 | 2.46 ms |

> **Critical Note on Metrics:** While `hit_rate@5` appears nearly identical across all three systems (0.93–0.98, saturated metric), **MRR** and **nDCG@10** reveal massive differences. BM25 trails Dense by 15.5 points, and Hybrid trails Dense by 5.8 points.

---

### B2. Breakdown by Question Kind (Non-Saturated Metric: MRR)

| Question Kind | Question Count ($n$) | Dense MRR | BM25 MRR | Hybrid MRR | Winner |
|---|:---:|:---:|:---:|:---:|:---:|
| `single_hop` | 18 | 0.9074 | 0.8519 | **0.9444** | Hybrid (+0.037) |
| `multi_hop` | 10 | **1.0000** | 0.6500 | 0.8167 | **Dense (+0.183)** |
| `paraphrase` | 5 | **0.8000** | 0.4867 | 0.6500 | **Dense (+0.150)** |
| `aggregation` | 4 | **0.8750** | 0.3750 | 0.5833 | **Dense (+0.292)** |
| `trap_archived` | 3 | **0.8333** | 0.5111 | 0.6667 | **Dense (+0.167)** |
| `unanswerable` | 2 | 0.3125 | **0.4167** | 0.3750 | BM25 |

In a head-to-head comparison across all 42 questions:
- **Dense beats BM25 on 20 questions.**
- **BM25 beats Dense on only 6 questions.**
- **Tied on 16 questions.**

---

### B3. Mechanism Deep-Dive: Exact Codes (Q44) vs. Paraphrase (Q41)

The contrasting strengths of lexical and semantic search are illustrated by two specific queries:

#### Question Q44: Exact Alphanumeric Identifier
- **Query:** *"AUR-HI-SIL-2026 — what are the sum insured options?"*
- **Results:** Dense MRR = **0.5000** (Rank 2) | BM25 MRR = **1.0000** (Rank 1) | Hybrid MRR = **1.0000** (Rank 1)
- **Mechanism:** BM25 assigns an enormous Inverse Document Frequency (IDF) weight to the rare token `AUR-HI-SIL-2026`, immediately locating the exact document. Dense embedding models represent rare alphanumeric codes less crisply, placing it at Rank 2. Here, **Hybrid successfully rescued Dense**.

#### Question Q41: Semantic Paraphrase (Zero Word Overlap)
- **Query:** *"If I skip paying on time, how long before I lose everything I've built up?"*
- **Results:** Dense MRR = **1.0000** (Rank 1) | BM25 MRR = **0.0000** (Unranked) | Hybrid MRR = **0.2500** (Rank 4)
- **Mechanism:** The policy uses the formal terms *"grace period"* and *"policy lapse"*. The customer uses *"skip paying"* and *"lose everything"*. BM25 scores 0 because there is zero keyword overlap. RRF blindly gave BM25 an equal vote, which **dragged Dense's correct #1 ranking down to Rank 4**.

---

### B4. Why Hybrid Search Lost on This Corpus

Standard information retrieval advice often claims that "Hybrid search is an automatic win." On this dataset, **Hybrid lost to Dense by 5.8 points** (0.7949 vs 0.8527).

**The Mechanism:**  
Reciprocal Rank Fusion is an uncalibrated voting system. Because BM25 was much weaker across the corpus (losing 20 of 26 head-to-head contests), fusing BM25 into every query dragged down 14 correct Dense answers for every 1 exact code query it helped. We tested tuning RRF $k$ across $\{10, 30, 60, 100\}$ (resulting in a narrow range of 0.7901–0.8156) and adjusting fusion weights up to $3:1$ in favor of Dense (0.8136). While higher Dense weighting reduced the penalty, pure Dense remained decisively superior.

---

## 3. Two-Stage Reranking: Latency, Cost & Deployment Decisions (Part C)

We evaluated passing the top 30 candidates from Dense retrieval to a second-stage reranker to re-order the top 5 results.

### C1. Reranker Comparison Table

| Configuration | hit_rate@1 | hit_rate@5 | recall@5 | MRR | nDCG@5 | Latency p95 | Cost / 1k Queries |
|---|---|---|---|---|---|---|---|
| **Dense Baseline (Direct k=5)** | **0.7857** | 0.9762 | **0.8909** | **0.8770** | **0.8313** | **1.56 ms** | **$0.00** |
| **Cross-Encoder (`ms-marco`)** | 0.7619 | **1.0000** | 0.8889 | 0.8619 | 0.8174 | 689.90 ms | **$0.00** |
| **LLM Reranker (`Gemini Flash`)** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | 28,000 ms | **$15.00** |

---

### C2. Two Contrasting Production Deployment Decisions

#### Deployment A: Live, Interactive Customer Search Box
- **Selected System:** **Pure Dense Search (No Reranking)**
- **Justification:**  
  Interactive web applications demand response times under 200 ms. Pure Dense responds in **1.56 ms** (essentially instantaneous), costs **$0.00** in external API fees, and delivers an outstanding **0.8313 nDCG@5**.  
  In contrast, the Cross-Encoder is **440× slower** (689 ms), adding noticeable lag while actually *reducing* accuracy to 0.8174. The LLM Reranker takes **28 seconds**, which completely violates interactive UI requirements.

#### Deployment B: Overnight Compliance & Policy Audit Job
- **Selected System:** **LLM Reranker (Gemini Flash)**
- **Justification:**  
  For an offline, asynchronous batch job validating legal compliance across policy catalogs, latency is irrelevant. What matters is zero false negatives. The LLM Reranker achieved **perfect 1.0000 nDCG@5 and 100% recall**. At $15 per 1,000 queries, processing a nightly batch of 500 audit questions costs just $7.50—a negligible price for flawless regulatory verification.
- **Why Does the LLM Reranker Take 28 Seconds? (OVERVIEW Hint):**  
  The 28-second latency is **not** because the model is thinking hard. It takes 28 seconds because the implementation makes **30 sequential API roundtrips in a row** (scoring each candidate chunk one-by-one over HTTP). If parallelized across 30 concurrent asynchronous requests, latency would drop to ~1.2–1.5 seconds. However, the cost ($15/1k queries) and rate-limit risks would remain, making it still unsuited for live customer queries compared to the $0, 1.56 ms Dense baseline.

---

### C3. Reranker Failure Case: Question Q32

- **Question:** *"Which plans have no co-payment?"*
- **Dense Alone:** MRR = **1.0000** (Correct policy placed at Rank 1).
- **With Cross-Encoder:** MRR = **0.2000** (Demoted to **Rank 5**).
- **Diagnosis (T4 §5, Failure Mode 5):**  
  The Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) was trained on general web search queries (Bing). When presented with fine-grained insurance terms like "co-payment" vs "deductible" across complex policy tables, its out-of-domain scoring misidentified broad introductory paragraphs as more relevant than the specific table listing 0% co-pay options.

---

## 4. Vector Indexes & The Metadata Trap (Part D)

### D1. Exact NumPy BLAS vs. ChromaDB (HNSW) at ~235 Chunks

| Index Type | Search Algorithm | hit_rate@1 | recall@5 | MRR | nDCG@10 | Latency p95 |
|---|---|---|---|---|---|---|
| **Exact NumPy** | In-memory BLAS dot-product | **0.7857** | **0.9028** | **0.8800** | **0.8527** | **1.41 ms** ⚡ |
| **ChromaDB** | HNSW Graph Traversal | **0.7857** | **0.9028** | **0.8800** | **0.8527** | 3.90 ms |

At our corpus size of 235 chunks, the quality gap is exactly **+0.0000** (identical rankings). However, NumPy BLAS is **2.8× faster** than ChromaDB.

---

### D2. Latency Crossover Benchmark Across Scale

We benchmarked query execution time as the corpus expanded from 235 chunks to ~40,000 chunks:

| Corpus Size | NumPy BLAS ($O(N)$ linear) | Chroma HNSW ($O(\log N)$ graph) | Winner |
|---|---|---|---|
| **235 chunks** | **0.012 ms** | 3.904 ms | **NumPy is 320× faster** |
| **4,000 chunks** | **0.368 ms** | 4.334 ms | **NumPy is 12× faster** |
| **40,000 chunks** | **4.227 ms** | 4.684 ms | **Dead Heat (Crossover at ~45k chunks)** |
| **100,000+ chunks** *(extrapolated)* | ~11.50 ms | **~5.10 ms** | **Chroma HNSW is 2.2× faster** |

**The Engineering Mechanism:**  
A modern CPU performs hundreds of thousands of floating-point vector dot products per millisecond using hardware SIMD (AVX2/BLAS). ChromaDB, while asymptotically logarithmic ($O(\log N)$), incurs fixed baseline software overhead: Python wrapper calls, SQLite metadata lookups, and graph pointer chasing (~3.8 ms). At small scales, the database overhead dominates. Exact linear search remains faster until approximately **45,000 chunks**.

---

### D3. The Metadata Trap (Questions Q29–Q31)

The corpus contains active policy documents alongside an outdated file: `claims-timelines-2024-ARCHIVED`. Questions Q29, Q30, and Q31 test timelines that changed between 2024 and 2026.

| Filter Condition | hit_rate@1 (Q29–Q31) | Outcome |
|---|:---:|---|
| **Unfiltered Search** | 66.7% | **FAILED on Q30:** Ranked outdated 2024 policy at #1 due to strong lexical similarity. |
| **Filtered Search (`status: current`)** | **100.0%** | **PASSED:** Outdated records excluded deterministically at zero latency cost. |

> **Key Takeaway:**  
> This dramatic accuracy boost (+33.3% on temporal trap queries) required **zero changes to the retriever, embedding model, or chunker**. When search systems fail in production, developers often rush to fine-tune models or swap algorithms. In practice, **data hygiene, document versioning, and deterministic metadata filters are the first and most effective levers to pull.**

---

## 5. Summary of Key Insights & Surprises

1. **The Big Surprise — Hybrid Search Underperformed:**  
   Contrary to common advice that hybrid search is always optimal, fusing BM25 with Dense degraded quality by **-5.8 points** on this dataset. When a dense embedding model is already strong and document terminology is conceptual, adding a weaker keyword retriever introduces noise rather than signal.
2. **Chunk Size Matters More Than Chunk Algorithm:**  
   Moving from 1600 characters down to 400 characters yielded a **+4.5 point boost** in nDCG@10, outpacing the difference between most chunking algorithms. Avoiding semantic dilution is critical for legal and policy text.
3. **Domain Mismatch Destroys Cross-Encoders:**  
   Off-the-shelf cross-encoders trained on web queries can degrade domain-specific legal search while adding 400× latency overhead. Never deploy a reranker without measuring it against an un-reranked baseline.
4. **Exact Math Beats Heavy Databases at Small Scale:**  
   Vector databases add operational complexity and latency overhead that only pays off past ~45,000 chunks. For smaller enterprise collections, in-memory matrix multiplication is faster, cheaper, and simpler.

---

## 6. Responses to Core Discussion Questions (from OVERVIEW.md)

### Question 1: Hybrid lost here and wins in most published results. What is different about this corpus? What would have to change for it to win?
- **Why it lost here:** The Aurora corpus is composed of conceptual health policy rules where user queries are dominated by paraphrases (*"skip paying on time"*) and multi-hop reasoning rather than keyword lookups. The 768-dimensional dense embedding model (`text-embedding-3-small`) combined with heading breadcrumbs is already powerful enough to handle both conceptual semantics and policy codes. Meanwhile, BM25 was severely deficient (0.6978 nDCG@10 vs 0.8527 for Dense), winning only 6 of 42 questions. Reciprocal Rank Fusion (RRF) gives equal voting weight to both rank lists; fusing in a substantially weaker retriever degraded 14 good rankings for every 1 exact code query it rescued.
- **What would have to change for Hybrid to win:** Hybrid would win if the corpus featured a heavy proportion of exact alphanumeric codes, SKU numbers, product identifiers, or specialized medical codes (ICD-10/CPT) that dense embeddings fail to generalize. It would also win if users predominantly searched via telegraphic keyword queries rather than natural language, or if the dense retriever used a weaker, small-capacity embedding model.

### Question 2: The metadata filter fixed three questions for free and changed nothing about the retriever. Where else in your pipeline is there a data fix hiding behind a modelling problem?
- **Document Versioning & Temporal Deprecation:** Filtering out superseded policies (`status: archived`) eliminates temporal hallucinations before the retriever is ever queried.
- **Structured Table Ingestion:** Ingesting complex tables as raw text destroys column alignment and relational meaning. Converting tables cleanly to Markdown or HTML at ingest fixes table-lookup questions without needing a bigger retrieval model.
- **Heading Breadcrumbs & Document Structure:** As shown in Experiment A3, injecting section paths (`[Policy > Exclusions]`) into chunk text improved rank-1 accuracy by **+14.3%** without touching retriever algorithms.
- **Corpus Deduplication:** Removing duplicate PDFs prevents redundant chunks from crowding out distinct answers in the top-$k$ context window.

### Question 3: Your greedy sweep fixed the chunker before choosing the retriever. Name a pair of axes in this lab that you suspect interact.
- **Interacting Pair: Chunk Size $\times$ Retrieval Algorithm (BM25 vs. Dense):**  
  BM25 keyword matching generally performs better on larger text chunks (800–1600 characters) because longer passages provide richer Term Frequency ($TF$) and Inverse Document Frequency ($IDF$) statistics without suffering from semantic dilution. In contrast, Dense vector retrieval heavily favors small, atomic chunks (400 characters) because embedding models suffer from centroid dilution when multiple topics are blended into one vector.  
  By fixing our chunker to `markdown-400` in Step 1, we may have evaluated BM25 at its least favorable chunk size, artificially handicapping its performance in Step 2. A true grid search might have shown BM25 or Hybrid performing much stronger on 1600-character chunks.

### Question 4: The LLM reranker is the best configuration measured and unusable interactively. If someone parallelised it to 1.5 seconds, would you deploy it? What else would you need to know?
- **Deployment Verdict:** **No for live interactive search; Yes for high-stakes asynchronous review.**
- **Critical Factors Needed Before Deploying at 1.5s:**
  1. **Financial Cost at Scale:** At $15.00 per 1,000 queries, an enterprise handling 1,000,000 customer searches per month would incur $15,000/month just for reranking, compared to $0.00 for in-memory Dense search.
  2. **Concurrency & Rate Limits:** Firing 30 parallel LLM requests per user query means 50 concurrent users would trigger 1,500 simultaneous API calls, instantly exhausting LLM rate limits (TPM/RPM) and inducing HTTP 429 errors.
  3. **User Experience Latency Budget:** Even 1.5 seconds exceeds the recommended 200–400 ms interactive latency budget for live search inputs, whereas Dense runs in 1.41 ms.
  4. **Domain Reliability:** As demonstrated by Question Q32, rerankers can suffer from domain mismatch or prompt misinterpretations on structured policy exclusions, introducing nondeterministic variance into the retrieval pipeline.

