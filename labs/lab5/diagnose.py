#!/usr/bin/env python3
"""Lab 5 — the failure classifier.

    python labs/lab5/diagnose.py --input reports/lab4.json
    python labs/lab5/diagnose.py --input reports/lab4.json --pareto

Implements the T4 §5 diagnostic tree. Everything that can be decided by code
is decided by code; mode 2 needs your eyes and the script says so.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from labs.lab3.search import load_corpus, load_questions  # noqa: E402

MODES = {
    1: "missing_content",
    2: "chunk_boundary",
    3: "embedding_mismatch",
    4: "ranking",
    5: "reranker",
    6: "generation",
    7: "presentation",
}


import re
from labs.lab4.evaluate import build_retriever  # noqa: E402


def answer_in_corpus(gold_answer: str, corpus: dict[str, str],
                     relevant_docs: list[str]) -> bool:
    """Mode 1 test. Checks whether the core factual entities and numbers in the
    gold answer actually exist in the relevant corpus documents.
    """
    if not relevant_docs:
        # If no relevant documents exist (pure unanswerable), content is not in corpus
        return False

    text = " ".join(corpus.get(d, "") for d in relevant_docs).lower()
    if not text:
        return False

    # Extract all numbers from gold answer
    numbers = [re.sub(r'[^\d]', '', t) for t in gold_answer.lower().split() if re.search(r'\d', t)]
    numbers = [n for n in numbers if n]

    # Extract meaningful words (length >= 4, excluding generic stopwords)
    stopwords = {"which", "there", "their", "about", "would", "under", "after", "before",
                 "other", "these", "those", "refuse", "aurora", "policy", "covered"}
    raw_words = [t.strip(".,;:()[]'\"-") for t in gold_answer.lower().split()]
    words = [w for w in raw_words if len(w) >= 4 and w not in stopwords]

    if not words and not numbers:
        return True

    # Check matches
    num_matches = sum(1 for n in numbers if n in text)
    word_matches = sum(1 for w in words if w in text)
    total = len(numbers) + len(words)

    # If key numbers exist and >= 35% of keywords exist, answer is confirmed in corpus
    if numbers and num_matches == len(numbers) and (word_matches / max(len(words), 1)) >= 0.3:
        return True

    return ((num_matches + word_matches) / max(total, 1)) >= 0.35


def classify(row: dict, q: dict, corpus: dict[str, str], *,
             retriever=None,
             gold_context_fixes_it: bool | None = None,
             in_top_30: bool | None = None,
             dropped_by_reranker: bool | None = None) -> tuple[int, str]:
    """Walk the T4 §5 diagnostic tree. Returns (mode, evidence)."""
    # Mode 7 first: right answer, wrong citation.
    if row.get("correctness", 0) >= 2 and not row.get("citations_valid", True):
        return 7, f"correct answer, invalid citations {row.get('invalid_citations')}"

    # Mode 1: is the answer even in the corpus?
    relevant_docs = q.get("relevant_docs", [])
    if not answer_in_corpus(q.get("gold_answer", ""), corpus, relevant_docs):
        return 1, f"gold answer content not found in relevant documents {relevant_docs}"

    # Check what was retrieved in Lab 4
    retrieved_docs = set(row.get("retrieved", []))
    
    # Mode 6: Check if generator had the primary relevant document(s) in context
    # If the system had the relevant document(s) in its top-5 context window,
    # retrieval succeeded -- the failure happened at generation (omission, brevity, refusal).
    primary_doc_retrieved = any(d in retrieved_docs for d in relevant_docs) if relevant_docs else False
    all_docs_retrieved = all(d in retrieved_docs for d in relevant_docs) if relevant_docs else False

    # If gold_context_fixes_it is explicitly provided and False -> Mode 6
    if gold_context_fixes_it is False:
        return 6, f"generator failed even with gold context (generation failure, score {row.get('correctness')})"

    if all_docs_retrieved or (primary_doc_retrieved and row.get("correctness", 0) > 0):
        # Generator had the required material in context, but omitted clauses, exceptions, or numbers
        return 6, f"primary gold doc(s) retrieved in top 5, but generator produced score {row.get('correctness')}/2 (generation omission/reasoning)"

    # If relevant docs were NOT retrieved in top 5, test top 30 retrieval
    if retriever:
        top_30 = [h.doc_id for h in retriever.search(q["question"], k=30)]
        missing_docs = [d for d in relevant_docs if d not in retrieved_docs]
        
        # Check if missing docs were found in top 30
        if any(d in top_30 for d in missing_docs):
            if dropped_by_reranker:
                return 5, f"gold doc(s) {missing_docs} was in top 30, but dropped by reranker"
            return 4, f"gold doc(s) {missing_docs} in top 30, but ranked outside top 5 (ranking error)"

        # Not in top 30: Test if searching the gold document's text retrieves it
        if missing_docs:
            sample_text = corpus.get(missing_docs[0], "")[:150]
            self_top30 = [h.doc_id for h in retriever.search(sample_text, k=30)]
            if missing_docs[0] in self_top30:
                return 3, f"gold doc {missing_docs[0]} not in top 30 for query, but found by chunk text (embedding mismatch)"

    return 2, "needs_human_check: open the chunks around the gold answer (chunk boundary)"


def pareto(tally: Counter) -> str:
    total = sum(tally.values()) or 1
    lines, cum = ["failure mode          n    share   cumulative"], 0
    for mode, n in tally.most_common():
        cum += n
        bar = "█" * round(30 * n / total)
        lines.append(f"{MODES[mode]:<20} {n:>3}   {n/total:>5.1%}   "
                     f"{cum/total:>5.1%}  {bar}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="reports/lab4.json")
    ap.add_argument("--pareto", action="store_true")
    ap.add_argument("--save", default="reports/lab5_diagnosis.json")
    args = ap.parse_args()

    rows = json.loads((ROOT / args.input).read_text(encoding="utf-8"))
    questions = {q["id"]: q for q in load_questions(include_unanswerable=True)}
    corpus = load_corpus()
    retriever = build_retriever()

    failures = [r for r in rows
                if r.get("correctness", 2) < 2 or not r.get("citations_valid", True)]
    print(f"{len(failures)} failures out of {len(rows)}\n")

    out, tally = [], Counter()
    for r in failures:
        q = questions[r["id"]]
        mode, evidence = classify(r, q, corpus, retriever=retriever)
        tally[mode] += 1
        out.append({"id": r["id"], "kind": q["kind"], "mode": mode,
                    "mode_name": MODES[mode], "evidence": evidence,
                    "question": q["question"], "answer": r["answer"][:300]})
        print(f"  {r['id']:<5} {MODES[mode]:<20} {evidence}")

    print("\n" + pareto(tally))
    print("\nCases marked needs_human_check are Part A2. Open them.")

    p = ROOT / args.save
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsaved -> {p}")


if __name__ == "__main__":
    main()
