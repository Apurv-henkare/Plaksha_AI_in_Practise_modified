#!/usr/bin/env python3
"""Test script for Step 3 prompt fix.
Demonstrates the output of the updated ANSWER_SYSTEM on key failed questions.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from labs.lab4.evaluate import build_retriever
from labs.lab4.rag import answer_question


def main():
    print("=" * 80)
    print("STEP 3 FIX VERIFICATION: Testing Generation Output")
    print("=" * 80)

    print("Building retriever...")
    retriever = build_retriever()
    print("Retriever ready.\n")

    test_queries = [
        ("Q04", "What is the waiting period for pre-existing diseases?"),
        ("Q20", "My mother is 63 and I want to add her to my policy. Which plans allow it and what changes?"),
        ("Q44", "AUR-HI-SIL-2026 — what are the sum insured options?"),
    ]

    for qid, qtext in test_queries:
        print(f"[{qid}] Question: {qtext}")
        print("-" * 80)
        ans = answer_question(qtext, retriever)
        print("Generated Answer:\n")
        print(ans.text)
        print("-" * 40)
        print(f"Citations Valid: {ans.citations_valid} | Citations Count: {ans.n_citations} | Refused: {ans.refused}")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
