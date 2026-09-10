
"""Lab 2 — the configurations under test.

Each variant is a callable `str -> dict`. `grid.py` runs them all through the
same harness, so the only thing that differs between rows of your table is the
thing you intended to differ.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from aip.llm import structured  # noqa: E402
from labs.lab1.extract import (  # noqa: E402
    SYSTEM_PROMPT, TicketRecord, apply_business_rules, extract_deterministic,
)

# ---------------------------------------------------------------------------
# A1 — your six chosen examples.
# ---------------------------------------------------------------------------
# TODO A1: choose 6 dev-set tickets. For EACH, write one line saying what it
#          teaches that prose cannot. Pick edges, not averages (T2 §2.2):
#            - the billing/complaint boundary
#            - a ticket with no policy number (teaches null)
#            - a Hinglish ticket
#            - a satisfied-but-urgent ticket (the sentiment/urgency trap)
#            - a ticket whose policy number is only in a quoted reply
#            - one you got wrong in Lab 1
FEW_SHOT_IDS: list[str] = [
    "T0054",  # teaches: refund demands resulting from agent mis-selling belong in 'complaint' not 'billing'
    "T0048",  # teaches: mentioning 'my policy' without an AUR-XXXXXXX identifier must return null
    "T0200",  # teaches: Hindi phrases ('Koi solution batayiye') flag language as 'hi-en' despite English prose
    "T0029",  # teaches: praise gives sentiment 'satisfied', and NCB query is 'information' with urgency 1
    "T0238",  # teaches: quoted reference 'SR-100238' is not an AUR policy number and portability is 'policy_change'
    "T0021",  # teaches: hospital desk portal downtime is urgency 5 and 'technical' despite anger and hospital setting
]

FEW_SHOT_EXAMPLES: dict[str, dict] = {
    "T0054": {
        "reasoning": (
            "Customer states the agent mis-sold the policy regarding the maternity waiting period and demands a full refund. "
            "Although a refund is demanded, service dissatisfaction stemming from agent mis-selling is classified under 'complaint', not 'billing'. "
            "Urgency is 4 due to severe dissatisfaction with sales conduct. Sentiment is angry. No policy number appears in AUR-XXXXXXX format, so policy_number is null. "
            "Product tier is not named (unknown). No phone or personal email (contains_pii is false). Language is English."
        ),
        "evidence": "Your agent mis-sold me this policy. Nobody told me maternity has a 5-month waiting period when I bought my policy. I want a full refund.",
        "category": "complaint",
        "urgency": 4,
        "sentiment": "angry",
        "product": "unknown",
        "language": "en",
        "policy_number": None,
        "contains_pii": False,
    },
    "T0048": {
        "reasoning": (
            "Customer is asking to add their mother as a dependent on their policy and asking about the premium impact. "
            "Adding a dependent is an endorsement/beneficiary change, so category is 'policy_change'. "
            "Urgency is 2 for a standard, non-urgent policy modification. Sentiment is neutral. "
            "The customer mentions 'my policy' without providing an AUR-XXXXXXX number, so policy_number must be null. "
            "Product tier is not specified (unknown). No phone or personal email (contains_pii is false). Language is English."
        ),
        "evidence": "Please add my mother as a dependent on my policy.",
        "category": "policy_change",
        "urgency": 2,
        "sentiment": "neutral",
        "product": "unknown",
        "language": "en",
        "policy_number": None,
        "contains_pii": False,
    },
    "T0200": {
        "reasoning": (
            "Customer is questioning a proportionate deduction made on an already settled claim for policy AUR-9674338. "
            "Disputes or questions regarding claim deductions belong to 'claims'. "
            "Urgency is 3 because the customer has an active issue and is waiting on an explanation. Sentiment is frustrated. "
            "The Hindi phrase 'Koi solution batayiye' mixed with English classifies language as 'hi-en'. "
            "Policy number AUR-9674338 is present. Mobile number 9686986118 constitutes PII (contains_pii is true). Product tier is not mentioned (unknown)."
        ),
        "evidence": "My claim on AUR-9674338 was settled at Rs 41800 but the hospital bill was much higher. Nobody explained the deduction.",
        "category": "claims",
        "urgency": 3,
        "sentiment": "frustrated",
        "product": "unknown",
        "language": "hi-en",
        "policy_number": "AUR-9674338",
        "contains_pii": True,
    },
    "T0029": {
        "reasoning": (
            "Customer opens by thanking Aurora for settling a claim quickly ('Thanks for settling my claim on my policy so quickly'), establishing 'satisfied' sentiment. "
            "The request itself is asking whether the claim affects their no-claim bonus (NCB), which is a general coverage/rules query without an active transaction, so category is 'information'. "
            "Urgency is 1 as there is no time limit or active issue. "
            "No AUR-XXXXXXX policy number is present (null). Mobile number 9131093871 means contains_pii is true. Product tier is unknown. Language is English."
        ),
        "evidence": "Just wanted to confirm whether my no-claim bonus is affected by this claim.",
        "category": "information",
        "urgency": 1,
        "sentiment": "satisfied",
        "product": "unknown",
        "language": "en",
        "policy_number": None,
        "contains_pii": True,
    },
    "T0238": {
        "reasoning": (
            "Customer is following up on a portability request submitted 21 days ago with an approaching renewal deadline. "
            "Plan portability falls under 'policy_change'. Urgency is 3 for an in-flight delayed request. Sentiment is frustrated. "
            "Product tier is explicitly mentioned as 'bronze'. "
            "The reference number 'SR-100238' in the quoted reply is a customer support service request, not an AUR insurance policy number, so policy_number is null. "
            "Mobile number 9591079365 means contains_pii is true. Language is English."
        ),
        "evidence": "I submitted a portability request 21 days ago and heard nothing. My existing policy renews soon.",
        "category": "policy_change",
        "urgency": 3,
        "sentiment": "frustrated",
        "product": "bronze",
        "language": "en",
        "policy_number": None,
        "contains_pii": True,
    },
    "T0021": {
        "reasoning": (
            "Customer is at a hospital insurance desk trying to show their policy, but the Aurora portal is down. "
            "Portal downtime and app issues are 'technical'. "
            "Because the customer is physically standing at the hospital desk in an emergency situation requiring resolution before morning, urgency is 5. "
            "Sentiment is angry ('Absolutely useless'). Product is 'gold'. "
            "'Jaldi karo please' is a code-mixed Hindi expression, classifying language as 'hi-en'. "
            "No AUR-XXXXXXX policy number is given (null). No phone or email (contains_pii is false)."
        ),
        "evidence": "Your portal has been down all morning and I am standing at the hospital insurance desk trying to show my Aurora Gold policy my policy.",
        "category": "technical",
        "urgency": 5,
        "sentiment": "angry",
        "product": "gold",
        "language": "hi-en",
        "policy_number": None,
        "contains_pii": False,
    },
}


def load_examples(ids: list[str]) -> list[dict]:
    rows = [json.loads(l) for l in
            (ROOT / "data/eval/extraction_dev.jsonl").open(encoding="utf-8")]
    by_id = {r["id"]: r for r in rows}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise KeyError(f"unknown example ids: {missing}")
    return [by_id[i] for i in ids]


def few_shot_block(ids: list[str], include_reasoning: bool = False) -> str:
    """Render the examples into the prompt.

    The example output format must be byte-identical to the format you are
    asking the model to produce. A mismatch here is a classic own goal.
    """
    examples = load_examples(ids)
    blocks = []
    for ex in examples:
        ex_id = ex["id"]
        spec = FEW_SHOT_EXAMPLES.get(ex_id)
        if not spec:
            continue
        if include_reasoning:
            out_obj = {
                "reasoning": spec["reasoning"],
                "evidence": spec["evidence"],
                "category": spec["category"],
                "urgency": spec["urgency"],
                "sentiment": spec["sentiment"],
                "product": spec["product"],
                "language": spec["language"],
                "policy_number": spec["policy_number"],
                "contains_pii": spec["contains_pii"],
            }
        else:
            out_obj = {
                "evidence": spec["evidence"],
                "category": spec["category"],
                "urgency": spec["urgency"],
                "sentiment": spec["sentiment"],
                "product": spec["product"],
                "language": spec["language"],
                "policy_number": spec["policy_number"],
                "contains_pii": spec["contains_pii"],
            }
        blocks.append(
            f"Ticket:\n{ex['input']}\n\nJSON Output:\n{json.dumps(out_obj, indent=2)}"
        )
    return "\n\n---\n\n".join(blocks)


# ---------------------------------------------------------------------------
# The variants
# ---------------------------------------------------------------------------
def zero_shot(ticket: str, tier: str = "SMALL") -> dict:
    """Lab 1 Part C, no examples. This is your baseline."""
    det_fields = extract_deterministic(ticket)
    try:
        model_rec = structured(ticket, schema=TicketRecord, system=SYSTEM_PROMPT, tier=tier)
        result = model_rec.model_dump()
    except Exception as exc:
        result = {
            "evidence": "",
            "category": "information",
            "urgency": 1,
            "sentiment": "neutral",
            "product": "unknown",
            "language": "en",
            "needs_human_review": True,
            "review_reason": str(exc),
        }
    result.update(det_fields)
    return apply_business_rules(result, ticket)


def few_shot(ticket: str, tier: str = "SMALL") -> dict:
    """zero_shot + the few-shot block."""
    det_fields = extract_deterministic(ticket)
    block = few_shot_block(FEW_SHOT_IDS, include_reasoning=False)
    prompt = (
        f"Here are reference examples of tickets and their expected extractions:\n\n"
        f"{block}\n\n"
        f"---\n\n"
        f"Now extract the JSON object for this ticket:\n\n"
        f"Ticket:\n{ticket}"
    )
    try:
        model_rec = structured(prompt, schema=TicketRecord, system=SYSTEM_PROMPT, tier=tier)
        result = model_rec.model_dump()
    except Exception as exc:
        result = {
            "evidence": "",
            "category": "information",
            "urgency": 1,
            "sentiment": "neutral",
            "product": "unknown",
            "language": "en",
            "needs_human_review": True,
            "review_reason": str(exc),
        }
    result.update(det_fields)
    return apply_business_rules(result, ticket)


class TicketRecordReasoned(TicketRecord):
    """Add a `reasoning: str` field FIRST (T2 §3.3).

    Pydantic keeps declaration order, and field order in the JSON Schema
    influences generation order. Putting reasoning first makes it condition the
    answer; putting it last makes it a post-hoc rationalisation. You want the
    first. Measure the difference in output tokens.
    """
    reasoning: str = Field(
        default="",
        description="Step-by-step reasoning explaining the situation, evidence, and customer intent before choosing classifications.",
    )

    @classmethod
    def model_json_schema(cls, *args, **kwargs):
        schema = super().model_json_schema(*args, **kwargs)
        if "properties" in schema and "reasoning" in schema["properties"]:
            schema["properties"] = {
                "reasoning": schema["properties"]["reasoning"],
                **{k: v for k, v in schema["properties"].items() if k != "reasoning"},
            }
        if "required" in schema and "reasoning" in schema["required"]:
            schema["required"] = ["reasoning"] + [k for k in schema["required"] if k != "reasoning"]
        return schema


def few_shot_reasoned(ticket: str, tier: str = "SMALL") -> dict:
    """few_shot with TicketRecordReasoned."""
    det_fields = extract_deterministic(ticket)
    block = few_shot_block(FEW_SHOT_IDS, include_reasoning=True)
    prompt = (
        f"Here are reference examples of tickets and their expected extractions (including step-by-step reasoning first):\n\n"
        f"{block}\n\n"
        f"---\n\n"
        f"Now extract the JSON object for this ticket (provide reasoning first):\n\n"
        f"Ticket:\n{ticket}"
    )
    try:
        model_rec = structured(prompt, schema=TicketRecordReasoned, system=SYSTEM_PROMPT, tier=tier)
        result = model_rec.model_dump()
    except Exception as exc:
        result = {
            "evidence": "",
            "category": "information",
            "urgency": 1,
            "sentiment": "neutral",
            "product": "unknown",
            "language": "en",
            "needs_human_review": True,
            "review_reason": str(exc),
        }
    result.update(det_fields)
    return apply_business_rules(result, ticket)


def cascade(ticket: str) -> dict:
    """SMALL first; escalate to MAIN on a trigger you choose.

    Triggers:
      - validation failed
      - evidence field empty or very short (< 10 chars)
      - two SMALL samples at T=0 and T=0.7 disagree on category or urgency

    Record which path each ticket took -- set rec['_path'] = 'small' | 'large'
    so grid.py can report the escalation rate.
    """
    res_small = zero_shot(ticket, tier="SMALL")
    escalate = False

    if res_small.get("needs_human_review") or len(res_small.get("evidence", "").strip()) < 10:
        escalate = True
    else:
        try:
            sample2_rec = structured(
                ticket, schema=TicketRecord, system=SYSTEM_PROMPT, tier="SMALL", temperature=0.7
            )
            sample2 = sample2_rec.model_dump()
            if (
                sample2.get("category") != res_small.get("category")
                or sample2.get("urgency") != res_small.get("urgency")
            ):
                escalate = True
        except Exception:
            escalate = True

    if escalate:
        res_main = zero_shot(ticket, tier="MAIN")
        res_main["_path"] = "large"
        return res_main
    else:
        res_small["_path"] = "small"
        return res_small


VARIANTS = {
    "zero_shot": lambda t: zero_shot(t, "SMALL"),
    "zero_shot_main": lambda t: zero_shot(t, "MAIN"),
    "few_shot": lambda t: few_shot(t, "SMALL"),
    "few_shot_main": lambda t: few_shot(t, "MAIN"),
    "few_shot_reasoned": lambda t: few_shot_reasoned(t, "SMALL"),
    "few_shot_reasoned_main": lambda t: few_shot_reasoned(t, "MAIN"),
    "cascade": cascade,
}
