#!/usr/bin/env python3
"""Lab 4 — your RAG pipeline.

Write this yourself. `aip/rag.py` is the reference implementation; look at it
after Part A, not before. Labs 5-7 build on whichever of the two you prefer,
but you must be able to explain every line of the one you use.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from aip.chunking import Chunk  # noqa: E402
from aip.guards import UNTRUSTED_SYSTEM_CLAUSE, delimit_untrusted  # noqa: E402
from aip.llm import chat  # noqa: E402
from aip.retrieval import Hit, Retriever, format_context  # noqa: E402

# The exact string the system must emit when it cannot answer. Exact, because
# downstream code detects refusal by matching it -- a paraphrase is a bug.
REFUSAL = "I don't have enough information in the provided sources to answer that."
ANSWER_SYSTEM = f"""\
You answer questions using ONLY the numbered sources provided below.
Rules, in priority order:
1. Grounding: Answer strictly and exclusively from the provided numbered sources. Never use outside or general knowledge.
2. Refusal & Partial Grounding:
   - If the provided sources contain NO information to answer the question, output EXACTLY this string:
     "{REFUSAL}"
   - If only PART of the question can be answered from the sources (e.g. coverage exists but limits are unstated), state the supported facts with citations, and state:
     "{REFUSAL}" regarding the missing details. Do not guess or invent unmentioned limits.
   - However, if the sources contain the relevant facts, plan details, or product codes, extract and answer with the supported facts rather than refusing.
3. Citations: Every factual sentence or claim must end with a citation to the specific source(s) supporting it, formatted as [1] or [2][5].
4. Valid Indices: Never cite a source number that was not provided in the context (only cite numbers between 1 and the total number of sources).
5. Contradictions: If different sources contradict or disagree with each other, explicitly describe the discrepancy and cite all conflicting sources.
6. Completeness & Structure: Be comprehensive, direct, and factual. Always explicitly include all relevant conditions, exceptions, optional riders, age restrictions, and specific limits found in the sources. Use clear bullet points if multiple conditions or plan options apply, rather than omitting details for brevity.
{UNTRUSTED_SYSTEM_CLAUSE}
"""



@dataclass
class Answer:
    question: str
    text: str
    hits: list[Hit] = field(default_factory=list)
    refused: bool = False
    citations_valid: bool = False
    invalid_citations: list[int] = field(default_factory=list)
    n_citations: int = 0
    truncated: bool = False
def validate_answer(text: str, n_sources: int, finish_reason: str | None = None) -> dict:
    """Validate answer citations and integrity deterministically in code."""
    truncated = (finish_reason == "length")
    clean_text = text.strip()
    # 1. Truncation check
    if truncated:
        return {
            "valid": False,
            "refused": False,
            "invalid_citations": [],
            "n_citations": 0,
            "truncated": True,
            "reason": "Answer truncated by model token length limit",
        }
    # 2. Empty output check
    if not clean_text:
        return {
            "valid": False,
            "refused": False,
            "invalid_citations": [],
            "n_citations": 0,
            "truncated": False,
            "reason": "Answer is empty",
        }
    # 3. Citation and Refusal checks
    cited_nums = [int(m) for m in re.findall(r"\[(\d+)\]", clean_text)]
    invalid_citations = sorted({c for c in cited_nums if c < 1 or c > n_sources})
    n_citations = len(cited_nums)
    is_refused = (REFUSAL in clean_text) or (REFUSAL[:40] in clean_text)
    # Pure refusal (no citations expected)
    if is_refused and n_citations == 0:
        return {
            "valid": True,
            "refused": True,
            "invalid_citations": [],
            "n_citations": 0,
            "truncated": False,
            "reason": "Valid full refusal",
        }
    # Partial refusal (has citations for supported part, and refusal phrase for missing part)
    if is_refused and n_citations > 0:
        if invalid_citations:
            return {
                "valid": False,
                "refused": True,
                "invalid_citations": invalid_citations,
                "n_citations": n_citations,
                "truncated": False,
                "reason": f"Partial refusal has invalid citations: {invalid_citations}",
            }
        return {
            "valid": True,
            "refused": True,
            "invalid_citations": [],
            "n_citations": n_citations,
            "truncated": False,
            "reason": "Valid partial refusal with supported citations",
        }
    # Standard non-refusal answer: must have at least one citation and no invalid citations
    if n_citations == 0:
        return {
            "valid": False,
            "refused": False,
            "invalid_citations": [],
            "n_citations": 0,
            "truncated": False,
            "reason": "Non-refusal answer contains zero citations",
        }
    if invalid_citations:
        return {
            "valid": False,
            "refused": False,
            "invalid_citations": invalid_citations,
            "n_citations": n_citations,
            "truncated": False,
            "reason": f"Invalid citations outside range 1..{n_sources}: {invalid_citations}",
        }
    return {
        "valid": True,
        "refused": False,
        "invalid_citations": [],
        "n_citations": n_citations,
        "truncated": False,
        "reason": "Valid cited answer",
    }


def answer_question(question: str, retriever: Retriever, *, k: int = 12,
                    final_k: int = 5, reranker=None, tier: str = "MAIN") -> Answer:
    """Retrieve -> (rerank) -> generate -> validate -> repair on failure.

    B3 Failure Policy:
    If validation fails (e.g. invalid index or missing citations), we retry once
    with an explicit corrective prompt. If it still fails, we fall back safely
    to REFUSAL. We NEVER return an answer with citations_valid=False and refused=False.
    """
    # 1. Retrieve candidates
    hits = retriever.search(question, k=k)
    if reranker is not None:
        hits = reranker.rerank(question, hits, k=final_k)
    else:
        hits = hits[:final_k]

    n_sources = len(hits)
    context_str = format_context(hits)
    user_prompt = f"Question: {question}\n\nRetrieved Sources:\n{delimit_untrusted(context_str)}"

    # 2. Generate initial answer
    res = chat(user_prompt, system=ANSWER_SYSTEM, tier=tier, return_full=True)
    text = res["text"]
    finish_reason = res.get("finish_reason")

    # 3. Validate
    v = validate_answer(text, n_sources, finish_reason)

    # 4. Repair policy on failure
    if not v["valid"]:
        correction_prompt = (
            f"{user_prompt}\n\n"
            f"Your previous attempt was rejected: {v['reason']}.\n"
            f"Please regenerate your answer following all rules strictly. Every factual sentence "
            f"MUST cite only numbers between [1] and [{n_sources}]. If the sources do not "
            f"contain the answer, output EXACTLY:\n\"{REFUSAL}\""
        )
        res = chat(correction_prompt, system=ANSWER_SYSTEM, tier=tier, return_full=True)
        text = res["text"]
        finish_reason = res.get("finish_reason")
        v = validate_answer(text, n_sources, finish_reason)

        # If it still fails after retry, fall back safely to refusal
        if not v["valid"]:
            text = REFUSAL
            v = {
                "valid": True,
                "refused": True,
                "invalid_citations": [],
                "n_citations": 0,
                "truncated": False,
                "reason": "Fallback to refusal after failed validation retry",
            }

    return Answer(
        question=question,
        text=text,
        hits=hits,
        refused=v["refused"],
        citations_valid=v["valid"],
        invalid_citations=v["invalid_citations"],
        n_citations=v["n_citations"],
        truncated=v["truncated"],
    )


def answer_with_gold_context(question: str, gold_docs: list[str], *,
                             tier: str = "MAIN") -> Answer:
    """E2: Same generator, but the context is the gold documents directly (no retrieval).
    The difference between this and answer_question() isolates the damage
    done by the retriever vs the generator ceiling.
    """
    hits = []
    for i, doc_text in enumerate(gold_docs, start=1):
        c = Chunk(text=doc_text, doc_id=f"gold_doc_{i}", chunk_id=f"gold_{i}")
        hits.append(Hit(chunk=c, score=1.0, source="gold", rank=i))
    n_sources = len(hits)
    context_str = format_context(hits)
    user_prompt = f"Question: {question}\n\nRetrieved Sources:\n{delimit_untrusted(context_str)}"
    res = chat(user_prompt, system=ANSWER_SYSTEM, tier=tier, return_full=True)
    text = res["text"]
    finish_reason = res.get("finish_reason")
    v = validate_answer(text, n_sources, finish_reason)
    if not v["valid"]:
        correction_prompt = (
            f"{user_prompt}\n\n"
            f"Your previous attempt was rejected: {v['reason']}.\n"
            f"Please regenerate your answer following all rules strictly. Every factual sentence "
            f"MUST cite only numbers between [1] and [{n_sources}]. If the sources do not "
            f"contain the answer, output EXACTLY:\n\"{REFUSAL}\""
        )
        res = chat(correction_prompt, system=ANSWER_SYSTEM, tier=tier, return_full=True)
        text = res["text"]
        finish_reason = res.get("finish_reason")
        v = validate_answer(text, n_sources, finish_reason)
        if not v["valid"]:
            text = REFUSAL
            v = {
                "valid": True,
                "refused": True,
                "invalid_citations": [],
                "n_citations": 0,
                "truncated": False,
                "reason": "Fallback to refusal after failed validation retry",
            }
    return Answer(
        question=question,
        text=text,
        hits=hits,
        refused=v["refused"],
        citations_valid=v["valid"],
        invalid_citations=v["invalid_citations"],
        n_citations=v["n_citations"],
        truncated=v["truncated"],
    )