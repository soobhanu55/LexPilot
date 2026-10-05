"""Offline tests: no LLM, Qdrant or Postgres needed.

The retrieval/classification benchmarks in evals/ need live services and run manually.
"""
import json
from datetime import datetime
from pathlib import Path

import pytest

from agents import checklist, deadlines
from agents.supervisor import route_to_agent
from config import cost_guard


@pytest.mark.parametrize("intent,node", [
    ("classify", "classifier_node"), ("question", "retriever_node"),
    ("checklist", "checklist_node"), ("inventory", "memory_node"),
    ("deadlines", "deadlines_node"), ("garbage", "retriever_node"),
])
def test_routing(intent, node):
    assert route_to_agent({"intent": intent}) == node


async def make_checklist(tier):
    state = {"classification_result": {"tier": tier}} if tier else {}
    return (await checklist.generate_checklist(state))["checklist"]


async def test_prohibited_is_single_critical_item():
    items = await make_checklist("prohibited")
    assert len(items) == 1 and items[0]["urgency"] == "critical" and items[0]["article"] == "Article 5"


async def test_high_risk_covers_core_articles():
    articles = {i["article"] for i in await make_checklist("high-risk")}
    assert articles == {f"Article {n}" for n in (9, 10, 11, 12, 13, 14, 15, 17)}


async def test_unknown_tier_falls_back_to_minimal():
    assert (await make_checklist(None))[0]["article"] == "Article 69"


class FrozenDT(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 5)


@pytest.mark.parametrize("tier,expected_urgency,expected_days", [
    ("prohibited", "critical", -610),      # ban date already passed
    ("limited-risk", "critical", -64),     # Aug 2026 enforcement already passed
    ("high-risk", "low", 423),             # 2 Dec 2027, > 365 days away
])
async def test_deadline_urgency(monkeypatch, tier, expected_urgency, expected_days):
    monkeypatch.setattr(deadlines, "datetime", FrozenDT)
    monkeypatch.setattr(deadlines, "get_inventory", lambda cid: [{"system_name": "s", "risk_tier": tier}])
    out = await deadlines.track_deadlines({"company_id": "c"})
    info = out["deadline_info"][0]
    assert (info["urgency"], info["days_remaining"]) == (expected_urgency, expected_days)


def test_cost_cap_refuses_after_budget():
    from types import SimpleNamespace as NS

    cost_guard.start_request()
    cap = cost_guard.CostCap()
    big = NS(generations=[[NS(message=NS(usage_metadata={"input_tokens": 400_000, "output_tokens": 100_000}))]])
    cap.on_chat_model_start({}, [])        # first call allowed
    cap.on_llm_end(big)                    # spends > MAX_USD_PER_REQUEST
    with pytest.raises(cost_guard.BudgetExceeded):
        cap.on_chat_model_start({}, [])


def test_ground_truth_is_well_formed():
    gt = json.loads((Path(__file__).parent.parent / "evals" / "ground_truth.json").read_text())
    assert len(gt) >= 10
    for t in gt:
        assert t["question"] and any(k in t for k in ("expected_tier", "expected_articles", "expected_answer_contains"))
