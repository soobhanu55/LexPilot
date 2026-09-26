"""Per-request cost cap for every Gemini call.

settings.get_llm() attaches CostCap to each model, so all agents (intent, classifier,
retriever, checklist, memory) and the final streamed answer share one budget per request.
run_agent() calls start_request() once; after that each LLM call adds its real token
usage, and the next call is refused once the request has spent MAX_USD_PER_REQUEST.
"""
from __future__ import annotations

import contextvars
import os

from langchain_core.callbacks import BaseCallbackHandler

# ponytail: flat list price for gemini-1.5-flash (USD per 1M tokens). Update if llm_model changes.
PRICE_PER_1M = {"input": 0.075, "output": 0.30}
MAX_USD_PER_REQUEST = float(os.environ.get("MAX_USD_PER_REQUEST", "0.01"))


class BudgetExceeded(RuntimeError):
    pass


# One mutable [usd] cell per request; a list so callbacks running in worker threads
# (copied context) still update the same object.
_spent: contextvars.ContextVar[list[float] | None] = contextvars.ContextVar("lexpilot_spent", default=None)


def start_request() -> None:
    _spent.set([0.0])


def spent_usd() -> float:
    cell = _spent.get()
    return cell[0] if cell else 0.0


def budget_exhausted() -> bool:
    return spent_usd() >= MAX_USD_PER_REQUEST


def cost_of(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * PRICE_PER_1M["input"] + output_tokens * PRICE_PER_1M["output"]) / 1_000_000


class CostCap(BaseCallbackHandler):
    raise_error = True  # make LangChain propagate BudgetExceeded instead of logging it

    def on_chat_model_start(self, serialized, messages, **kwargs):
        if budget_exhausted():
            raise BudgetExceeded(f"cost cap reached: ${spent_usd():.4f} of ${MAX_USD_PER_REQUEST:.4f} for this request")

    def on_llm_end(self, response, **kwargs):
        cell = _spent.get()
        if cell is None:
            return  # called outside run_agent (scripts, evals): track nothing
        for gens in response.generations:
            for g in gens:
                usage = getattr(getattr(g, "message", None), "usage_metadata", None) or {}
                cell[0] += cost_of(usage.get("input_tokens", 0), usage.get("output_tokens", 0))


if __name__ == "__main__":
    # Self-check: two calls under budget pass, then the cap refuses the next one.
    from types import SimpleNamespace as NS

    os.environ["MAX_USD_PER_REQUEST"] = "0.01"
    start_request()
    cap = CostCap()
    big = NS(generations=[[NS(message=NS(usage_metadata={"input_tokens": 40_000, "output_tokens": 10_000}))]])
    cap.on_chat_model_start({}, [])
    cap.on_llm_end(big)  # 0.003 + 0.003 = $0.006
    cap.on_chat_model_start({}, [])
    cap.on_llm_end(big)  # $0.012, over the cap
    try:
        cap.on_chat_model_start({}, [])
        raise SystemExit("FAIL: cap did not trigger")
    except BudgetExceeded as e:
        print("ok:", e)
