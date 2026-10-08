"""Per-request tracing: agent spans, LLM-call spans with tokens and cost, and the /traces endpoint."""
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk

from agents import supervisor
from backend_api import index
from config import cost_guard, telemetry
from test_supervisor_and_api import collect, scripted


async def test_a_chat_request_leaves_agent_spans_and_returns_its_request_id(fake_llm):
    fake_llm.responder = scripted("classify")
    done = (await collect("Is our chatbot high risk?", "sess-trace"))[-1]
    assert done["type"] == "done" and len(done["request_id"]) == 12
    t = telemetry.get_trace(done["request_id"])
    assert {"agent.detect_intent", "agent.classifier"} <= set(t["summary"]["agents"])
    assert t["summary"]["errors"] == 0 and all(s["ms"] >= 0 for s in t["spans"])
    assert done["usage"] == t["summary"]


async def test_each_request_gets_its_own_trace(fake_llm):
    fake_llm.responder = scripted("classify")
    a = (await collect("first", "s1"))[-1]["request_id"]
    b = (await collect("second", "s2"))[-1]["request_id"]
    assert a != b and telemetry.get_trace(a)["spans"] and telemetry.get_trace(b)["spans"]
    assert not {s["id"] for s in telemetry.get_trace(a)["spans"]} & {s["id"] for s in telemetry.get_trace(b)["spans"]}


def model(cb, tokens=None):
    msg = AIMessage(content="ok", usage_metadata=tokens or {"input_tokens": 1000, "output_tokens": 200, "total_tokens": 1200})
    return FakeMessagesListChatModel(responses=[msg], callbacks=[cb])


async def test_llm_calls_record_tokens_and_cost_from_the_response():
    telemetry.start_trace("llm-1")
    await model(telemetry.TraceCallback("gemini-1.5-flash")).ainvoke("hi")
    s = telemetry.get_trace("llm-1")["summary"]
    assert s["llm_calls"] == 1 and s["input_tokens"] == 1000 and s["output_tokens"] == 200
    assert s["cost_usd"] == pytest.approx(cost_guard.cost_of(1000, 200), abs=1e-6)


async def test_a_model_without_a_known_price_is_left_unpriced():
    telemetry.start_trace("llm-2")
    await model(telemetry.TraceCallback("some-other-model")).ainvoke("hi")
    assert telemetry.get_trace("llm-2")["summary"]["cost_usd"] is None


def test_a_failed_llm_call_is_an_error_span():
    telemetry.start_trace("llm-3")
    cb, run = telemetry.TraceCallback("gemini-1.5-flash"), uuid.uuid4()
    cb.on_chat_model_start({}, [], run_id=run)
    cb.on_llm_error(TimeoutError("deadline"), run_id=run)
    t = telemetry.get_trace("llm-3")
    assert t["summary"]["errors"] == 1 and t["spans"][0]["attributes"]["error.type"] == "TimeoutError"


async def test_llm_spans_nest_under_the_agent_that_made_them():
    telemetry.start_trace("llm-4")

    @telemetry.traced_node("demo")
    async def node(state):
        await model(telemetry.TraceCallback("gemini-1.5-flash")).ainvoke("hi")
        return state

    await node({})
    spans = telemetry.get_trace("llm-4")["spans"]
    assert [(s["name"], s["depth"]) for s in spans] == [("agent.demo", 0), ("llm.call", 1)]


def test_traces_endpoint(fake_llm):
    client = TestClient(index.app)
    assert client.get("/traces/does-not-exist").status_code == 404
    telemetry.start_trace("api-1")
    with telemetry.span("agent.demo"):
        pass
    body = client.get("/traces/api-1").json()
    assert body["request_id"] == "api-1" and body["summary"]["agents"] == ["agent.demo"]
    assert client.get("/backend-api/traces/api-1").status_code == 200  # also served under the Vercel prefix


class StreamingModel(BaseChatModel):
    """Streams like Gemini: text chunks first, token usage on the last chunk."""

    @property
    def _llm_type(self):
        return "streaming-fake"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise NotImplementedError

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        for text in ("Answer ", "text."):
            yield ChatGenerationChunk(message=AIMessageChunk(content=text))
        usage = {"input_tokens": 700, "output_tokens": 40, "total_tokens": 740}
        yield ChatGenerationChunk(message=AIMessageChunk(content="", usage_metadata=usage))


async def test_streamed_answers_are_counted_from_the_last_chunk():
    telemetry.start_trace("stream-1")
    llm = StreamingModel(callbacks=[telemetry.TraceCallback("gemini-1.5-flash")])
    text = "".join([c.content async for c in llm.astream("hi")])
    s = telemetry.get_trace("stream-1")["summary"]
    assert text == "Answer text." and s["llm_calls"] == 1 and (s["input_tokens"], s["output_tokens"]) == (700, 40)
    assert s["cost_usd"] == pytest.approx(cost_guard.cost_of(700, 40), abs=1e-6)
