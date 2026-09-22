#!/usr/bin/env python3
"""Test script for Step 3: Refusal in both directions and Q37 handling."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from labs.lab3.search import load_questions
from labs.lab4.evaluate import build_retriever
from labs.lab4.rag import answer_question


def main():
    print("=" * 70)
    print("STEP 3: EVALUATING REFUSAL BEHAVIOR ON UNANSWERABLE QUESTIONS")
    print("=" * 70)

    retriever = build_retriever()
    all_questions = load_questions(include_unanswerable=True)

    unanswerable = [q for q in all_questions if q["id"] in ["Q36", "Q37", "Q38", "Q39", "Q40"]]
    answerable = [q for q in all_questions if q["id"] not in ["Q36", "Q37", "Q38", "Q39", "Q40"]]

    refused_unanswerable = 0
    print("\n--- Part C1 & C2: The 5 Unanswerable Questions (Q36-Q40) ---\n")
    for q in unanswerable:
        a = answer_question(q["question"], retriever)
        is_refused = a.refused
        if is_refused:
            refused_unanswerable += 1
        print(f"[{q['id']}] Question: {q['question']}")
        print(f"     Status: refused={a.refused}, citations_valid={a.citations_valid}, n_citations={a.n_citations}")
        print(f"     Answer:\n     {a.text}\n")

    # Evaluate refusal on answerable set
    print("--- Part C3: Measuring Refusals on Answerable Questions ---")
    wrongful_refusals = 0
    for q in answerable:
        a = answer_question(q["question"], retriever)
        if a.refused:
            wrongful_refusals += 1
            print(f"  [Notice] Wrongful refusal on {q['id']}: {q['question'][:60]}...")

    total_refusals = refused_unanswerable + wrongful_refusals
    refusal_recall = refused_unanswerable / len(unanswerable)
    refusal_precision = (refused_unanswerable / total_refusals) if total_refusals > 0 else 1.0

    print("\n" + "=" * 70)
    print("REFUSAL METRICS SUMMARY:")
    print("=" * 70)
    print(f"Unanswerable questions correctly declined: {refused_unanswerable}/{len(unanswerable)}")
    print(f"Refusal Recall:    {refusal_recall:.3f} ({refused_unanswerable}/{len(unanswerable)})  [Target: >= 0.800 (4/5)]")
    print(f"Wrongful refusals on answerable questions: {wrongful_refusals}/{len(answerable)}")
    print(f"Refusal Precision: {refusal_precision:.3f} ({refused_unanswerable}/{total_refusals})  [Target: >= 0.700]")
    print("=" * 70)


if __name__ == "__main__":
    main()
