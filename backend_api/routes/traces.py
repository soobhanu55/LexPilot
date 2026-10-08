from fastapi import APIRouter, HTTPException

from config.telemetry import get_trace

router = APIRouter(prefix="/traces", tags=["Traces"])


@router.get("/{request_id}")
def request_trace(request_id: str):
    """Spans for one chat request (the id is in the stream's final `done` event): per-agent and per-LLM-call
    latency, tokens, cost and errors. Only the most recent requests are kept in memory."""
    trace = get_trace(request_id)
    if not trace["spans"]:
        raise HTTPException(status_code=404, detail="No trace for this request")
    return trace
