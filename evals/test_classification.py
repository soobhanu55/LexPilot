import pytest
import json
import asyncio
import os
from agents.classifier import classify_ai_system
from agents.state import LexAgentState
from config.settings import settings

def load_ground_truth():
    path = os.path.join(os.path.dirname(__file__), "ground_truth.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.mark.asyncio
async def test_classification_accuracy():
    gt = load_ground_truth()
    classification_tasks = [t for t in gt if "expected_tier" in t]
    
    correct_tiers = 0
    
    for task in classification_tasks:
        state: LexAgentState = {
            "user_message": task["question"],
            "company_id": "test_company",
            "session_id": "test_session",
            "agent_trace": [],
        }
        
        result_state = await classify_ai_system(state)
        res = result_state.get("classification_result", {})
        
        assigned_tier = res.get("tier", "").lower()
        expected = task["expected_tier"].lower()
        
        assert expected in assigned_tier, f"Failed on '{task['question']}': Expected {expected}, got {assigned_tier}"
        correct_tiers += 1
        
        # Article check
        articles = res.get("articles", [])
        if task.get("expected_articles"):
            found = any(ea in " ".join(articles) for ea in task["expected_articles"])
            assert found, f"Failed to find expected articles for '{task['question']}'"

    print(f"\nClassification eval passed: {correct_tiers}/{len(classification_tasks)}")
