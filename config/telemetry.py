"""Tracing: OpenTelemetry spans for every agent node and every LLM call, with latency, tokens and cost.

Finished spans are kept per request in a small in-process ring buffer (GET /traces/{request_id}); set
OTEL_EXPORTER_OTLP_ENDPOINT to also ship them to Langfuse, Jaeger or Tempo. LLM spans use the OpenTelemetry GenAI
attribute names. `TraceCallback` is attached to every model in settings.get_llm(), next to the per-request cost cap.
"""
from __future__ import annotations

import contextvars
import functools
import os
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from typing import Any, Callable

from langchain_core.callbacks import BaseCallbackHandler
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from config.cost_guard import cost_of

MAX_TRACES = 200
PRICED_MODEL = "gemini-1.5-flash"  # the only model PRICE_PER_1M describes; any other model is reported unpriced

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("lexpilot_request_id", default=None)


def start_trace(request_id: str) -> None:
    _request_id.set(request_id)


class RingExporter(SpanExporter):
    """Keeps finished spans grouped by request id; the oldest request is dropped past MAX_TRACES."""

    def __init__(self) -> None:
        self._by_request: OrderedDict[str, list[dict]] = OrderedDict()
        self._lock = threading.Lock()

    def export(self, spans) -> SpanExportResult:
        with self._lock:
            for s in spans:
                rid = (s.attributes or {}).get("request.id", "-")
                self._by_request.setdefault(rid, []).append({
                    "id": f"{s.context.span_id:016x}",
                    "parent": f"{s.parent.span_id:016x}" if s.parent else None,
                    "name": s.name,
                    "start_ns": s.start_time,
                    "ms": round((s.end_time - s.start_time) / 1e6, 2),
                    "error": s.status.status_code == trace.StatusCode.ERROR,
                    "attributes": {k: v for k, v in (s.attributes or {}).items() if k != "request.id"},
                })
            while len(self._by_request) > MAX_TRACES:
                self._by_request.popitem(last=False)
        return SpanExportResult.SUCCESS

    def spans(self, request_id: str) -> list[dict]:
        with self._lock:
            return sorted((dict(s) for s in self._by_request.get(request_id, [])), key=lambda s: s["start_ns"])


ring = RingExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(ring))
if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):  # pragma: no cover - needs a collector
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
_tracer = _provider.get_tracer("lexpilot")


@contextmanager
def span(name: str, **attrs: Any):
    with _tracer.start_as_current_span(name) as sp:
        sp.set_attribute("request.id", _request_id.get() or "-")
        for k, v in attrs.items():
            sp.set_attribute(k, v)
        try:
            yield sp
        except Exception as exc:
            sp.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)[:200]))
            sp.set_attribute("error.type", type(exc).__name__)
            raise


def traced_node(name: str) -> Callable:
    """Decorator for a graph node (an async function of the state): one span per execution."""

    def wrap(fn):
        @functools.wraps(fn)
        async def inner(state, *a, **kw):
            with span(f"agent.{name}"):
                return await fn(state, *a, **kw)

        return inner

    return wrap


class TraceCallback(BaseCallbackHandler):
    """One span per chat-model call: model, tokens, cost, latency, and the error if it failed."""

    def __init__(self, model: str) -> None:
        self.model, self._started = model, {}

    def on_chat_model_start(self, serialized, messages, *, run_id=None, **kwargs):
        self._started[run_id] = time.time_ns()

    def _span(self, run_id, error: BaseException | None = None, usage: dict | None = None):
        sp = _tracer.start_span("llm.call", start_time=self._started.pop(run_id, time.time_ns()))
        sp.set_attribute("request.id", _request_id.get() or "-")
        sp.set_attribute("gen_ai.request.model", self.model)
        tin, tout = int((usage or {}).get("input_tokens", 0)), int((usage or {}).get("output_tokens", 0))
        sp.set_attribute("gen_ai.usage.input_tokens", tin)
        sp.set_attribute("gen_ai.usage.output_tokens", tout)
        if self.model == PRICED_MODEL:
            sp.set_attribute("llm.cost_usd", round(cost_of(tin, tout), 6))
        if error is not None:
            sp.set_status(trace.Status(trace.StatusCode.ERROR, str(error)[:200]))
            sp.set_attribute("error.type", type(error).__name__)
        sp.end()

    def on_llm_end(self, response, *, run_id=None, **kwargs):
        usage = {"input_tokens": 0, "output_tokens": 0}
        for gens in response.generations:
            for g in gens:
                u = getattr(getattr(g, "message", None), "usage_metadata", None) or {}
                usage["input_tokens"] += u.get("input_tokens", 0)
                usage["output_tokens"] += u.get("output_tokens", 0)
        self._span(run_id, usage=usage)

    def on_llm_error(self, error, *, run_id=None, **kwargs):
        self._span(run_id, error=error)


def get_trace(request_id: str) -> dict:
    spans = ring.spans(request_id)
    by_id = {s["id"]: s for s in spans}
    for s in spans:
        depth, p = 0, s["parent"]
        while p in by_id:
            depth, p = depth + 1, by_id[p]["parent"]
        s["depth"] = depth
        s.pop("start_ns")
    llm = [s for s in spans if s["name"] == "llm.call"]
    costs = [s["attributes"].get("llm.cost_usd") for s in llm]
    return {
        "request_id": request_id,
        "spans": spans,
        "summary": {
            "llm_calls": len(llm),
            "llm_ms": round(sum(s["ms"] for s in llm), 2),
            "input_tokens": sum(s["attributes"]["gen_ai.usage.input_tokens"] for s in llm),
            "output_tokens": sum(s["attributes"]["gen_ai.usage.output_tokens"] for s in llm),
            "cost_usd": None if any(c is None for c in costs) else round(sum(costs), 6),  # None: a call used an unpriced model
            "agents": [s["name"] for s in spans if s["name"].startswith("agent.")],
            "errors": sum(1 for s in spans if s["error"]),
        },
    }
