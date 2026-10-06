"""Agent nodes with a scripted LLM and stubbed database/Qdrant: parsing, fallbacks, traces and error handling."""
import json

import pytest

from agents import classifier, memory_agent, retriever
from agents.supervisor import detect_intent


def state(**kw):
    return {"user_message": "msg", "company_id": "c1", "session_id": "s1", "agent_trace": [], **kw}


# --- classifier -------------------------------------------------------------------------------

CLS = {"tier": "high-risk", "matched_article": "Article 6", "matched_annex_entry": "Annex III", "reasoning": "r", "confidence": "high"}


@pytest.mark.parametrize("wrap", [lambda s: s, lambda s: f"```json\n{s}\n```", lambda s: f"```\n{s}\n```"])
async def test_classifier_parses_plain_and_fenced_json(fake_llm, wrap):
    fake_llm.responder = lambda p: wrap(json.dumps(CLS))
    out = await classifier.classify_ai_system(state(user_message="CV screening"))
    assert out["classification_result"]["tier"] == "high-risk" and out["classification_result"]["articles"] == ["Article 6"]
    assert out["agent_trace"][-1]["agent"] == "classifier" and "error" not in out


async def test_classifier_handles_garbage_without_crashing(fake_llm):
    fake_llm.responder = lambda p: "I think it is probably risky."
    out = await classifier.classify_ai_system(state())
    assert out["classification_result"]["tier"] == "unknown" and out["error"].startswith("Classification failed")


async def test_classifier_defaults_missing_fields(fake_llm):
    fake_llm.responder = lambda p: "{}"
    out = await classifier.classify_ai_system(state())
    assert out["classification_result"]["tier"] == "minimal-risk"


async def test_classifier_sends_the_user_description_in_the_prompt(fake_llm):
    fake_llm.responder = lambda p: json.dumps(CLS)
    await classifier.classify_ai_system(state(user_message="A drone inspector"))
    assert "A drone inspector" in fake_llm.llm.prompts[0]


# --- intent -----------------------------------------------------------------------------------

@pytest.mark.parametrize("reply,intent", [
    ('{"intent": "classify"}', "classify"), ('```json\n{"intent": "deadlines"}\n```', "deadlines"),
    ("not json", "question"), ("{}", "question"),
])
async def test_detect_intent(fake_llm, reply, intent):
    fake_llm.responder = lambda p: reply
    assert (await detect_intent(state()))["intent"] == intent


# --- inventory memory agent ----------------------------------------------------------------------------

async def test_inventory_list_formats_systems(fake_llm, monkeypatch):
    fake_llm.responder = lambda p: '{"action": "list"}'
    monkeypatch.setattr(memory_agent, "get_inventory", lambda cid: [
        {"system_name": "Chatbot", "risk_tier": "limited-risk", "description": "d", "compliance_status": "pending"}])
    out = await memory_agent.manage_inventory(state())
    assert "**Chatbot** (limited-risk)" in out["final_answer"] and out["inventory_action"]["action"] == "list"


async def test_inventory_add_uses_classification_tier(fake_llm, monkeypatch):
    fake_llm.responder = lambda p: '{"action": "add", "system_name": "Scorer", "description": "Scores loans"}'
    saved = {}

    def fake_upsert(company, name, desc, tier, articles):
        saved.update(company=company, name=name, tier=tier, articles=articles)
        return {"system_name": name}

    monkeypatch.setattr(memory_agent, "upsert_ai_system", fake_upsert)
    out = await memory_agent.manage_inventory(state(classification_result={"tier": "high-risk", "articles": ["Article 6"]}))
    assert saved == {"company": "c1", "name": "Scorer", "tier": "high-risk", "articles": ["Article 6"]}
    assert "Added **Scorer**" in out["final_answer"]


async def test_inventory_unknown_action_and_failure_paths(fake_llm):
    fake_llm.responder = lambda p: '{"action": "delete"}'
    assert "not fully supported" in (await memory_agent.manage_inventory(state()))["final_answer"]
    fake_llm.responder = lambda p: "garbage"
    out = await memory_agent.manage_inventory(state())
    assert out["error"].startswith("Memory agent failed") and out["final_answer"] == "Could not process inventory request."


# --- retriever -----------------------------------------------------------------------------------

class FakeEmbeddings:
    async def aembed_query(self, q):
        return [0.1, 0.2]


class FakeQdrant:
    def __init__(self, hits=None, fail=False):
        self.hits, self.fail = hits or [], fail

    async def search(self, **kw):
        if self.fail:
            raise RuntimeError("qdrant down")
        return self.hits


def hit(article_id, score):
    from types import SimpleNamespace as NS
    return NS(score=score, payload={"article_id": article_id, "title": f"T{article_id}", "text": f"text of {article_id}"})


@pytest.fixture
def retrieval_env(monkeypatch, fake_llm):
    import networkx as nx
    from config.settings import Settings

    g = nx.DiGraph()
    g.add_edges_from([("Article 6", "Article 9"), ("Article 9", "Article 17")])
    monkeypatch.setattr(retriever, "GRAPH", g)
    monkeypatch.setattr(retriever, "CHUNKS_DICT", {a: {"article_id": a, "title": a, "text": f"graph text {a}"} for a in g.nodes})
    monkeypatch.setattr(retriever, "init_resources", lambda: None)
    monkeypatch.setattr(Settings, "get_embeddings", lambda self: FakeEmbeddings())
    return fake_llm


def install_qdrant(monkeypatch, client):
    from config.settings import Settings
    monkeypatch.setattr(Settings, "get_async_qdrant_client", lambda self: client)


async def test_retriever_expands_via_graph_and_reranks(retrieval_env, monkeypatch):
    install_qdrant(monkeypatch, FakeQdrant([hit("Article 6", 0.9)]))
    scores = {"Article 6": "5", "Article 9": "9", "Article 17": "2"}
    retrieval_env.responder = lambda p: next(v for k, v in scores.items() if f"text of {k}" in p or f"graph text {k}" in p)
    out = await retriever.retrieve_articles(state(user_message="high-risk obligations"))
    ids = [a["article_id"] for a in out["retrieved_articles"]]
    assert ids == ["Article 9", "Article 6", "Article 17"]  # graph neighbours added, sorted by rerank score
    assert set(out["graph_neighbors"]) == {"Article 9", "Article 17"}
    assert out["agent_trace"][-1]["output"]["retrieved"] == ids


async def test_retriever_falls_back_to_dense_score_when_rerank_fails(retrieval_env, monkeypatch):
    install_qdrant(monkeypatch, FakeQdrant([hit("Article 6", 0.9), hit("Article 5", 0.7)]))
    retrieval_env.responder = lambda p: "not a number"
    out = await retriever.retrieve_articles(state())
    top = {a["article_id"]: a["rerank_score"] for a in out["retrieved_articles"]}
    assert top["Article 6"] == pytest.approx(9.0) and top["Article 5"] == pytest.approx(7.0)


async def test_retriever_survives_a_dense_search_failure(retrieval_env, monkeypatch):
    install_qdrant(monkeypatch, FakeQdrant(fail=True))
    out = await retriever.retrieve_articles(state())
    assert out["retrieved_articles"] == [] and out["error"].startswith("Dense retrieval failed")


async def test_retriever_returns_at_most_six_articles(retrieval_env, monkeypatch):
    install_qdrant(monkeypatch, FakeQdrant([hit(f"Article {i}", 0.9 - i / 100) for i in range(30, 38)]))
    retrieval_env.responder = lambda p: "5"
    assert len((await retriever.retrieve_articles(state()))["retrieved_articles"]) == 6
