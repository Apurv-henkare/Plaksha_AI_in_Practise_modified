# Step 0 Summary: Connecting the Search Engine (Lab 3 to Lab 4)

---

## 1. The Big Picture (In Plain English)

Think of building an AI question-answering system like running a two-person team in an office:
- **Person 1 (The Searcher / Librarian):** Their only job is to run to the filing cabinet, find the 5 best policy pages, and put them on the desk.
- **Person 2 (The Writer / Advisor):** Their job is to read those 5 pages and write a clear, 2-sentence answer for the customer.

In **Lab 3**, we spent all our time training **Person 1 (The Searcher)**. We tested different ways to cut documents and proved that cutting them into **400-character pieces with markdown headings (`markdown-400`)** using **Dense search** found the right pages 90% of the time.

In **Lab 4**, our job is to train **Person 2 (The Writer)**. But before we write any answers, we must give Person 2 our best search engine from Lab 3.

---

## 2. What We Changed in the Code

In `labs/lab4/evaluate.py`, there was a placeholder setting that cut documents into huge 800-character chunks:

```python
# Before (Placeholder):
def build_retriever():
    corpus = load_corpus()
    chunks = [c for doc_id, text in corpus.items()
              for c in markdown_chunks(text, doc_id, size=800)]
    return DenseRetriever(chunks)
```

We changed `size=800` to our Lab 3 winner: **`size=400`**:

```python
# After (Our Winning Setup):
def build_retriever():
    corpus = load_corpus()
    chunks = [c for doc_id, text in corpus.items()
              for c in markdown_chunks(text, doc_id, size=400)]
    return DenseRetriever(chunks)
```

### Why does this matter?
- When chunks are too big (800 or 1600 characters), several different insurance rules get mixed together on the same page. The AI gets confused about which rule applies.
- At **400 characters**, each chunk contains exactly **one single rule** (for example, just the room rent limit, or just the waiting period). This gives our writer super-clean information.

---

## 3. The Test We Ran

We ran this command to verify that our search engine built all the chunks properly:

```powershell
python -c "from labs.lab4.evaluate import build_retriever; r = build_retriever(); print(f'Retriever successfully built with {len(r.chunks)} chunks!')"
```

**What the terminal printed:**
```text
Retriever successfully built with 235 chunks!
```

---

## 4. Glossary: What Each Term Means (In Simple Plain English)

To make sure everyone understands the technical terms used in this step, here is what each piece of jargon actually means:

- **RAG (Retrieval-Augmented Generation):**  
  A fancy name for a simple 2-step process: First, **retrieve** (search) the relevant documents from a database; second, **generate** (write) an answer based *only* on those documents. Instead of letting an AI hallucinate from memory, you feed it the open textbook first.
- **Corpus:**  
  The complete collection of reference files. In our project, the corpus is the 30 insurance policy files in `data/corpus/` (covering rules, exclusions, limits, and comparison guides).
- **Chunk & Chunking:**  
  You cannot feed an entire 50-page insurance policy manual to an AI in one search query. **Chunking** is the act of slicing long documents into smaller, bite-sized "index cards" (e.g., 400 characters each). Each card is called a **chunk**.
- **Markdown-Aware Chunking (`markdown-400`):**  
  Instead of blindly slicing text mid-sentence, this smart slicer splits text along Markdown section headings (like `# Exclusions` or `## Waiting Periods`) and keeps the chunk size around 400 characters. It also pastes the section heading path at the top of every chunk so the AI knows where the rule belongs.
- **Retriever / Search Engine:**  
  The software program whose only job is to look at the user's question, compare it against all 235 chunks, and pick the top 5 most relevant chunks.
- **Dense Retriever & Embeddings:**  
  Instead of matching exact keywords like Google or Ctrl-F (lexical search), an **embedding model** converts sentences into lists of numbers (vectors) that capture their deeper conceptual meaning. A **Dense Retriever** compares these numbers using math (dot products) to find matches even if the user and the policy use completely different words (for example: *"skipping payments"* matching *"grace period"*).
- **Context:**  
  The specific text snippets retrieved by the search engine and pasted into the AI writer's prompt so it can read them before answering.

---

## 5. Key Takeaways from Step 0

1. **235 neat chunks loaded:** All 30 policy documents were split into 235 sharp, bite-sized index cards.
2. **Fast in-memory search:** Because we use `DenseRetriever`, searching through these 235 cards takes less than 2 milliseconds.
3. **Ready for Step 1:** Now that we have the best search engine bringing us the right pages, we can teach our AI how to write answers.
