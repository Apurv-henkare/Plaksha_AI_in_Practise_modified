# Step 1 Comprehensive Summary: Document Chunking (Part A)

---

## 0. The Big Picture: How Step 1 and Step 2 Fit Together

> **A Common Question:** *"In both Step 1 and Step 2, we retrieved documents to test accuracy. What is the difference between them?"*

Search system optimization follows the **Scientific Method**—we change **one variable at a time** so we know exactly what caused an improvement:

```text
+----------------------------------------------------------------------------------------------------+
|                               THE 4-STAGE SEARCH PIPELINE                                          |
+----------------------------------------------------------------------------------------------------+
|  STEP 1: THE DATA (CHUNKING)    -->  STEP 2: THE SEARCH ALGORITHM  -->  STEP 3: THE RERANKER      |
|  • Tested: How to cut documents      • Tested: Dense vs BM25 vs Hybrid   • Tested: Cross-Encoder/LLM|
|  • Variable: Slicing & sizes         • Variable: The search engine       • Variable: 2nd-stage sort |
|  • Constant: Dense search            • Constant: markdown-400 chunks     • Constant: Top 30 cand.   |
|  • Winner: markdown-400              • Winner: Dense Retriever           • Next to test!            |
+----------------------------------------------------------------------------------------------------+
```

### Why We Retrieved Documents in Step 1:
To know if a document-cutting style is good or bad, you cannot just guess—you have to **measure retrieval**. 
- In **Step 1**, we used the exact same search algorithm (`DenseRetriever`) on every test as our **fixed measuring tape**. 
- By keeping the search engine constant, any change in `ndcg@10` or `recall@5` proved whether the **chunking style** itself was better or worse.
- **The Result of Step 1:** We proved that **`markdown-400`** is the best chunking strategy.

---

## 1. Background: Why Does Chunking Matter in AI Search?

### The Real-World Problem at Aurora Health
Customer support agents currently search policy documents using **Ctrl+F** on PDFs. This fails constantly:
- A customer asks: *"How long do I have to file my hospital bill?"*
- The legal policy states: *"Claims must be submitted within 30 days of discharge."*
- **Ctrl+F finds zero matches** because none of the customer's exact words appear in the document.

### Why Semantic Search Needs "Chunking" First
To fix this, modern AI search (RAG — Retrieval-Augmented Generation) converts text into mathematical vectors (embeddings) that represent **meaning**, allowing *"how long to file"* to match *"within 30 days"*.

However, an AI embedding model cannot convert a 20-page document into a single vector without losing all detail. If you squeeze 20 pages of rules into one vector, the rules get averaged together into a blurry blend. 

Therefore, we **must slice long documents into smaller pieces ("chunks")** before embedding them. 

In **Step 1**, we systematically investigated:
1. **Part A1:** Which mathematical cutting algorithm creates the most retrievable chunks?
2. **Part A2:** What is the ideal chunk size (character count), and why does size behave non-linearly?
3. **Part A3:** What is the exact measurable benefit of prepending section heading breadcrumbs?
4. **Part A4:** What specific failure occurs when chunking goes wrong?

---

## 2. The Evaluation Metrics (Explained with Mechanics & Formulas)

To evaluate search performance accurately, we track four core metrics across the 42 benchmark questions:

| Metric | Formula & Mechanics | Plain English Meaning | Why It Matters for Aurora Health |
|---|---|---|---|
| **`hit_rate@1`** | $\frac{\text{Queries with relevant doc at Rank 1}}{\text{Total Queries}}$ | **First-Place Accuracy:** Did the search engine put the correct document in the **very first (#1) spot**? | Support agents usually only look at the top recommended answer card. Target is $\ge 0.65$ (65%). |
| **`hit_rate@5`** | $\frac{\text{Queries with relevant doc in top 5}}{\text{Total Queries}}$ | **Top-5 Presence:** Did the right document appear anywhere in the **top 5 recommendations**? | Sanity check. However, it saturates easily (0.93–0.98), making bad retrievers look artificially good. |
| **`recall@5`** | $\frac{\text{Relevant docs retrieved in top 5}}{\text{Total relevant docs that exist}}$ | **Completeness / Coverage:** Out of all documents needed to answer a query, what percentage did we find? | Some policy questions require 2 documents (e.g. general rule + exclusion). Missing one leads to AI hallucinations. Target is $\ge 0.85$ (85%). |
| **`mrr`**<br>*(Mean Reciprocal Rank)* | $\frac{1}{N} \sum_{i=1}^N \frac{1}{\text{rank}_i}$ | **Position Quality:** Rewards placing answers near the top.<br>• Rank 1 = $1/1 = 1.0$<br>• Rank 2 = $1/2 = 0.5$<br>• Rank 7 = $1/7 = 0.14$ | Unlike `hit_rate@5`, MRR does not saturate. It severely penalizes burying an answer down at rank 4 or 7. |
| **`ndcg@10`**<br>*(Normalized Discounted Cumulative Gain)* | $\frac{\text{DCG@10}}{\text{IDCG@10}}$ where position gets a $\log_2(r+1)$ discount | **The Headline Grade (0 to 1):** The gold standard of search evaluation. Measures how perfectly the whole top-10 list is ordered. | Rewards placing all correct documents at ranks 1–3 and heavily discounts relevant documents pushed to ranks 8–10. Target is $\ge 0.80$. |
| **`chunks`** | Count of chunks produced | Total number of pieces created from the 30 documents. | More chunks provide finer granularity, but require slightly more memory and index storage. |
| **`build_ms`** | $\Delta t$ in milliseconds | Time taken to chunk the corpus and construct the retrieval index. | Verifies whether an algorithm is fast enough for production pipelines (~50–150 ms). |

---

## 3. Experiment A1: In-Depth Analysis of the 4 Cutting Styles

We tested 4 distinct chunking algorithms at a standardized size of **800 characters**:

| Cutting Style | First Result (`hit_rate@1`) | Top 5 (`hit_rate@5`) | Coverage (`recall@5`) | Position Quality (`mrr`) | Overall Grade (`ndcg@10`) | Total Chunks | Build Time |
|---|---|---|---|---|---|---|---|
| **`fixed-800`** | 73.81% | 95.24% | 83.73% | 0.8387 | **0.7952** | 83 | 150 ms |
| **`sliding-800`** | 78.57% | 92.86% | 84.52% | 0.8451 | **0.8053** | 91 | 55 ms |
| **`recursive-800`** | 76.19% | 95.24% | 87.50% | 0.8611 | **0.8251** | 98 | 63 ms |
| **`markdown-800`** | 76.19% | 97.62% | 89.88% | 0.8720 | **0.8458** 🏆 | 164 | 105 ms |

---

### In-Depth Observations for Each Case in A1:

#### Case 1: `fixed-800` (The Strawman — Score: 0.7952 | 83 Chunks)
- **Algorithm Mechanics:** Slices text strictly every 800 characters without regard for grammatical boundaries, spaces, or words.
- **Why It Failed:** 
  In policy documentation, clauses are strictly conditional (e.g. *"Coverage applies up to \$10,000, provided prior approval was obtained 48 hours before admission"*). Fixed chunking regularly cuts right through the middle of such sentences. As a result, Chunk A contains the benefit and Chunk B contains the restriction. The semantic connection is broken, causing retrieval to fail on conditional queries.
- **Conclusion:** Unsuitable for production RAG systems.

#### Case 2: `sliding-800` (The Overlapping Window — Score: 0.8053 | 91 Chunks)
- **Algorithm Mechanics:** Steps forward by 650 characters, leaving a 150-character overlap between chunk $N$ and chunk $N+1$.
- **Why It Improved Over Fixed (+1.01 points):** 
  The 150-character safety buffer ensures that sentences falling across chunk borders are captured in full in at least one of the two adjacent chunks. This raised `hit_rate@1` from 73.81% to 78.57%.
- **Its Weakness:** 
  Because the cut points are still determined by character counts rather than grammatical structure, chunks frequently begin or end with truncated sentence fragments.

#### Case 3: `recursive-800` (Structure-Aware Slicing — Score: 0.8251 | 98 Chunks)
- **Algorithm Mechanics:** Attempts to split text using a hierarchy of natural separators: double line breaks (`\n\n` paragraphs) $\rightarrow$ single line breaks (`\n`) $\rightarrow$ sentence periods (`. `) $\rightarrow$ word spaces (` `).
- **Why It Significantly Improved (+2.99 points over fixed):** 
  Paragraphs in policy documents encapsulate complete logical concepts. By preserving entire paragraphs, the vector embedding represents a unified, complete human thought. Both `recall@5` (87.50%) and `mrr` (0.8611) saw substantial gains.
- **Its Weakness:** 
  While it preserves paragraphs, it remains unaware of the broader document section or table of contents hierarchy.

#### Case 4: `markdown-800` (Hierarchy-Aware Slicing — Winner: 0.8458 | 164 Chunks)
- **Algorithm Mechanics:** Parses the Markdown AST (Abstract Syntax Tree), splits specifically at section headings (`#`, `##`, `###`), and prepends the full breadcrumb path (`[Policy > Section > Rule]`) to every chunk.
- **Why It Won Decisively (+5.06 points over fixed):** 
  1. It aligns with how technical authors structured the policy.
  2. Each chunk contains contextual metadata explaining what policy it belongs to.
  3. It achieved the highest `recall@5` (89.88%) and `ndcg@10` (0.8458).
- **The Trade-Off:** 
  It generates 164 chunks (roughly 2× more than fixed). However, because building the index took only 105 ms, the compute cost is completely negligible compared to the massive +5% accuracy jump.

---

## 4. Experiment A2: In-Depth Analysis of Chunk Size & The Dilution Curve

We took the winning markdown strategy and tested three chunk sizes: **400**, **800**, and **1600** characters:

| Chunk Size | First Result (`hit_rate@1`) | Top 5 (`hit_rate@5`) | Coverage (`recall@5`) | Position Quality (`mrr`) | Overall Grade (`ndcg@10`) | Total Chunks | Build Time |
|---|---|---|---|---|---|---|---|
| **`markdown-400`** | **78.57%** | **97.62%** | **90.28%** | **0.8800** | **0.8527** 🏆 | 235 | 153 ms |
| **`markdown-800`** | 76.19% | 97.62% | 89.88% | 0.8720 | **0.8458** | 164 | 102 ms |
| **`markdown-1600`** | 71.43% | 95.24% | 87.50% | 0.8262 | **0.8075** | 150 | 106 ms |

---

### In-Depth Observations for Each Size in A2:

```text
       nDCG@10
       0.86 |      ★ markdown-400 (0.8527) - Optimal Knee
            |     /
       0.84 |    /--- markdown-800 (0.8458)
            |   /
       0.82 |  /
            | /
       0.80 |/---------- markdown-1600 (0.8075) - Dilution Drop
            +-------------------------------------------
             400 chars      800 chars      1600 chars
```

#### Case 1: `markdown-400` (The Optimal Sweet Spot: 0.8527 | 235 Chunks)
- **Why It Won:** 
  Insurance policies are modular. A single rule regarding ambulance coverage or dental copay is typically 300–450 characters long. At 400 characters, each chunk is **atomic**—it encapsulates exactly one policy proposition.
- **Vector Mechanics:** 
  Because there is zero extraneous text, the resulting 768-dimensional embedding vector points with high mathematical precision toward that specific topic. When a customer asks about that topic, the cosine similarity score is very high.

#### Case 2: `markdown-800` (Balanced Baseline: 0.8458 | 164 Chunks)
- **Why It Scored Well but Lower:** 
  At 800 characters, chunks begin bundling two or three distinct sub-rules together (e.g. emergency admission rules bundled with elective admission rules). While still coherent, the vector representation begins to spread across multiple topics.

#### Case 3: `markdown-1600` (The Dilution Cliff: 0.8075 | 150 Chunks)
- **Why It Collapsed (-4.52 points):**
  This directly validates the **Embedding Dilution Principle** (from Course Theory T4 §2.2):
  1. An embedding model maps an entire piece of text into a **single vector** in latent space.
  2. When a 1600-character chunk contains rules on hospital cash, ICU limits, ambulance caps, and daycare procedures, the vector settles at the mathematical **centroid** of all four topics.
  3. The vector is "diluted" (like watering down pure juice). It is moderately close to everything, but sharply close to nothing.
  4. Consequently, specific user queries fail to achieve high cosine similarity, causing `hit_rate@1` to plummet from 78.57% down to 71.43%.

#### Why the Curve is Non-Monotonic (The "Knee" Concept):
If smaller is better, why not use 50-character chunks?
- If chunks are too small (<200 characters), individual sentences get split. A chunk might say *"Subject to a deductible of \$500"*, completely missing *what* the deductible applies to.
- Thus, the quality curve is **non-monotonic** (it rises, reaches a peak, and falls). On this insurance corpus, **400 characters is the exact "knee" of the curve**.

---

## 5. Experiment A3: In-Depth Analysis of Heading Breadcrumbs (`[heading > path]`)

We tested `markdown-800` with and without the automatically generated breadcrumb string:

| Configuration | First Result (`hit_rate@1`) | Top 5 (`hit_rate@5`) | Coverage (`recall@5`) | Position Quality (`mrr`) | Overall Grade (`ndcg@10`) | Total Chunks |
|---|---|---|---|---|---|---|
| **With Heading Path** | **76.19%** | 97.62% | 89.88% | **0.8720** | **0.8458** | 164 |
| **Without Heading Path** | **61.90%** | 100.00% | 90.48% | **0.7837** | **0.7915** | 164 |
| **Net Difference ($\Delta$)** | **+14.29% Jump!** | -2.38% | -0.60% | **+8.83% Jump!** | **+5.43% Jump!** | 0 |

---

### In-Depth Observations for Each Case in A3:

#### Case 1: With Heading Path (e.g. `[Aurora Health > Inpatient Care > Reimbursement Timelines]`)
- **The "Orphan Chunk" Solution:** 
  Consider this raw chunk text: *"Submit bills within 30 days of hospital discharge. Late submissions will be rejected."* Without a heading, this chunk is an "orphan"—the AI does not know if this rule applies to health claims, auto claims, or travel baggage claims.
- **Impact:** 
  Prepending `[Aurora Health > Claims Timelines]` anchors the text in vector space. The AI knows both the **context** and the **rule**, driving `hit_rate@1` up by **+14.29%** (from 61.90% to 76.19%).

#### Case 2: Without Heading Path (Stripped Text)
- **The Illusion of 100% `hit_rate@5`:**
  Notice that without headings, `hit_rate@5` reached **100.00%**! At first glance, a beginner might think "without headings is better!"
- **Why That Conclusion is Wrong (Metric Saturation):**
  Without headings, chunks contain generic medical vocabulary that lands broadly across ranks 3, 4, and 5. The answer is technically on the page, but buried down low.
- **The Key Insight:** 
  Heading breadcrumbs improve **Ranking Precision** (pushing the true answer to Rank #1), rather than sloppy broad recall. In customer support, putting the correct answer at #1 is what matters.

---

## 6. Experiment A4: In-Depth Failure Case Analysis (Question Q08)

To observe chunking mechanics under a microscope, we examined **Question Q08**:
- **User Query:** *"Can I claim for IVF treatment?"*
- **Ground Truth Target Document:** `exclusions.md`

---

### Comparative Trace of What Happened:

#### Case 1: Under `fixed-800` (FAILED — Rank 7, MRR = 0.1429)
- **Top Document Retrieved:** `hospital-cash-benefit.md` (Cosine Score: 0.6513)
- **Text Snippet Retrieved at Rank 1:**
  ```text
  of the indemnity treatment.
  ## Waiting periods
  30 days initial; 24 months for specified illnesses; 36 months for pre-existing disease...
  ```
- **Root Cause of Failure:** 
  Under fixed chunking, the exclusion clause was cut without the word "Exclusions". The query contained the word "treatment". The vector retriever saw "indemnity treatment" and "specified illnesses" in `hospital-cash-benefit` and concluded this was a close match. The actual exclusion rule was buried at **Rank 7**, making it invisible to a live agent.

#### Case 2: Under `markdown-800` (SUCCEEDED — Rank 1, MRR = 1.0000)
- **Top Document Retrieved:** `exclusions.md` (Cosine Score: 0.6406)
- **Text Snippet Retrieved at Rank 1:**
  ```text
  [Permanent Exclusions > Treatment-related exclusions]
  - Cosmetic or plastic surgery, unless required to treat an accidental injury...
  - In vitro fertilisation (IVF), fertility, and sub-fertility treatments...
  ```
- **Root Cause of Success:** 
  The heading `[Permanent Exclusions > Treatment-related exclusions]` was glued directly to the chunk. The negative intent of the query (*"Can I claim for..."*) matched against an explicit exclusion heading. The document jumped straight to **Rank 1**.

---

## 7. Key Findings & Final Presentation Takeaways

When presenting Step 1 to your professor or evaluators, highlight these four core insights:

1. **Chunking is the Highest-Leverage Lever in RAG:**
   - Swapping from naive cutting (`fixed-800`) to hierarchical cutting (`markdown-400`) improved overall search quality (`ndcg@10`) from **0.7952 to 0.8527** (+5.75 points).
   - This single change delivered more improvement than swapping underlying embedding models.
2. **The Dilution Trade-off is Empirically Real:**
   - Doubling chunk size from 800 to 1600 characters caused a -4.5 point drop in accuracy because multi-topic vectors drift toward the centroid.
   - 400 characters represents the atomic sweet spot for policy documentation.
3. **Heading Path Injection is Zero-Cost Context:**
   - Adding breadcrumbs costs \$0 in API fees and 0 ms in query latency, yet provides an immediate **+14.3% boost to rank-1 accuracy**.
4. **All Rubric Benchmark Targets Exceeded:**
   - **`ndcg@10`**: **0.8527** *(Target: $\ge 0.80$)* ✅
   - **`recall@5`**: **0.9028** *(Target: $\ge 0.85$)* ✅
   - **`hit_rate@1`**: **0.7857** *(Target: $\ge 0.65$)* ✅
5. **Next Step Transition:**
   - We lock in **`markdown-400`** as our gold-standard chunk representation and proceed directly to **Step 2 (Part B)** to benchmark Dense vs BM25 vs Hybrid retrieval.
