"""The compiled LangGraph supervisor (streamed SSE events) and the FastAPI layer, with a scripted LLM and stubbed DB."""
import json

import pytest
from fastapi.testclient import TestClient

from agents import deadlines, supervisor
from backend_api import index
from backend_api.routes import audit, chat, inventory


def events(chunks):
    return [json.loads(c[len("data: "):]) for c in chunks]


async def collect(message, session):
    return events([c async for c in supervisor.run_agent(message, "company-1", session)])


def scripted(intent, classification=None):
    def respond(prompt):
        if "Determine the user's intent" in prompt:
            return json.dumps({"intent": intent})
        if "analyzing an AI system" in prompt:
            return json.dumps(classification or {"tier": "limited-risk", "matched_article": "Article 50", "reasoning": "chatbot"})
        return "{}"
    return respond


async def test_classify_intent_streams_status_citations_answer_done(fake_llm):
    fake_llm.responder = scripted("classify")
    ev = await collect("Is our support chatbot high risk?", "sess-classify")
    assert [e["type"] for e in ev][0] == "status" and ev[-1]["type"] == "done"
    assert any(e["type"] == "citations" and e["articles"] == ["Article 50"] for e in ev)
    assert "".join(e["text"] for e in ev if e["type"] == "answer") == "Answer text [Article 5]."
    assert {t["agent"] for t in ev[-1]["trace"]} == {"classifier"}


async def test_checklist_intent_cites_the_obligations(fake_llm):
    fake_llm.responder = scripted("checklist")
    ev = await collect("What do we need to do?", "sess-checklist")
    cited = next(e for e in ev if e["type"] == "citations")["articles"]
    assert cited == ["Article 69"]  # no classification yet: minimal-risk fallback checklist


async def test_deadlines_intent_uses_the_inventory(fake_llm, monkeypatch):
    fake_llm.responder = scripted("deadlines")
    monkeypatch.setattr(deadlines, "get_inventory", lambda cid: [{"system_name": "Scorer", "risk_tier": "high-risk"}])
    ev = await collect("When are our deadlines?", "sess-deadlines")
    done = ev[-1]
    assert done["trace"][0]["agent"] == "deadlines" and done["trace"][0]["output"] == {"tracked_systems": 1}
    assert any("Deadline Info" in p and "Scorer" in p for p in fake_llm.llm.prompts)


async def test_budget_exhaustion_short_circuits_the_final_answer(fake_llm, monkeypatch):
    fake_llm.responder = scripted("classify")
    monkeypatch.setattr(supervisor, "budget_exhausted", lambda: True)
    ev = await collect("anything", "sess-budget")
    answers = [e["text"] for e in ev if e["type"] == "answer"]
    assert len(answers) == 1 and answers[0].startswith("Stopped: this request hit its cost cap") and ev[-1]["type"] == "done"


# --- FastAPI ----------------------------------------------------------------------------------------

@pytest.fixture
def client():
    return TestClient(index.app, raise_server_exceptions=False)


def test_health_endpoints(client):
    for path in ("/", "/backend-api", "/health"):
        assert client.get(path).json()["status"] == "ok"


def test_unhandled_errors_become_json_500(client, monkeypatch):
    def boom(company_id):
        raise RuntimeError("db is down")

    monkeypatch.setattr(inventory, "get_inventory", boom)
    r = client.get("/inventory/c1")
    assert r.status_code == 500 and r.json()["error"] == "Internal Server Error" and r.json()["type"] == "RuntimeError"


ITEM = {"id": "1", "system_name": "Bot", "description": "d", "risk_tier": "limited-risk", "classification_articles": ["Article 50"],
        "compliance_status": "pending", "created_at": "t", "updated_at": "t"}


def test_inventory_list_add_status_and_missing(client, monkeypatch):
    monkeypatch.setattr(inventory, "get_inventory", lambda cid: [ITEM])
    assert client.get("/inventory/c1").json()[0]["system_name"] == "Bot"
    monkeypatch.setattr("db.queries.get_company", lambda cid: {"id": cid})
    monkeypatch.setattr(inventory, "upsert_ai_system", lambda c, n, d, t, a: {"system_name": n, "risk_tier": t})
    assert client.post("/inventory/c1", params={"system_name": "X", "description": "d"}).json() == {"system_name": "X", "risk_tier": "unknown"}
    monkeypatch.setattr(inventory, "update_compliance_status", lambda sid, st: {"id": sid, "compliance_status": st})
    assert client.patch("/inventory/c1/7", params={"status": "compliant"}).json()["compliance_status"] == "compliant"
    monkeypatch.setattr(inventory, "update_compliance_status", lambda sid, st: None)
    assert client.patch("/inventory/c1/7", params={"status": "x"}).status_code == 404


def test_audit_list_and_export_header(client, monkeypatch):
    monkeypatch.setattr(audit, "get_audit_log", lambda cid, limit=50: [{"agent_name": "classifier", "limit": limit}])
    assert client.get("/audit/c1", params={"limit": 5}).json() == [{"agent_name": "classifier", "limit": 5}]
    r = client.get("/audit/c1/export")
    assert r.headers["content-disposition"] == "attachment; filename=audit_c1.json" and r.json()[0]["limit"] == 1000


def test_chat_streams_events_and_saves_the_trace(client, monkeypatch):
    saved = []

    async def fake_run(message, company_id, session_id):
        yield 'data: {"type": "status"}\n\n'
        yield 'data: ' + json.dumps({"type": "done", "trace": [{"agent": "classifier"}]}) + "\n\n"

    monkeypatch.setattr(chat, "run_agent", fake_run)
    monkeypatch.setattr(chat, "save_trace_to_db", lambda company, session, trace: saved.append((company, session, trace)))
    r = client.post("/chat", json={"message": "hi", "company_id": "c1", "session_id": "s1"})
    frames = [line[len("data: "):] for line in r.text.splitlines() if line.startswith("data: ")]
    assert r.status_code == 200 and [json.loads(f)["type"] for f in frames] == ["status", "done"]  # one 'data:' prefix, valid JSON
    assert saved == [("c1", "s1", [{"agent": "classifier"}])]


def test_chat_validates_the_request_body(client):
    assert client.post("/chat", json={"message": "hi"}).status_code == 422


async def test_session_memory_carries_classification_into_a_later_checklist(fake_llm):
    fake_llm.responder = scripted("classify", {"tier": "prohibited", "matched_article": "Article 5", "reasoning": "social scoring"})
    await collect("We score citizens", "sess-memory")
    fake_llm.responder = scripted("checklist")
    cited = next(e for e in await collect("What must we do?", "sess-memory") if e["type"] == "citations")["articles"]
    assert cited == ["Article 5"]
