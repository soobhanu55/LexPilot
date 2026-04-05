import pytest
import json
import asyncio
import os
import time
from agents.retriever import retrieve_articles
from agents.state import LexAgentState

def load_ground_truth():
    path = os.path.join(os.path.dirname(__file__), "ground_truth.json")
    with open(path, "r") as f:
        return json.load(f)

@pytest.mark.asyncio
async def test_retrieval_performance():
    # Requires running Qdrant + embedded act chunks
    gt = load_ground_truth()
    retrieval_tasks = [t for t in gt if t.get("expected_articles")]
    
    latencies = []
    
    print("\nBenchmark:")
    print("Question | Expected | Retrieved | Latency (ms) | Hit")
    
    for task in retrieval_tasks:
        state: LexAgentState = {
            "user_message": task["question"],
            "company_id": "test",
            "session_id": "test",
            "agent_trace": [],
        }
        
        start_t = time.time()
        res_state = await retrieve_articles(state)
        latency = int((time.time() - start_t) * 1000)
        latencies.append(latency)
        
        retrieved_ids = [a["article_id"] for a in res_state.get("retrieved_articles", [])]
        
        expected_set = set(task["expected_articles"])
        hit = len(expected_set.intersection(set(retrieved_ids))) > 0
        
        print(f"'{task['question'][:20]}...' | {task['expected_articles']} | {retrieved_ids} | {latency}ms | {hit}")
        
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
    assert p95_latency < 3000, f"p95 latency limit exceeded: {p95_latency}ms > 3000ms"
