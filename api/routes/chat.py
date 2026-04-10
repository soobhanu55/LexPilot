import json
import asyncio
from fastapi import APIRouter, Request, BackgroundTasks
from sse_starlette.sse import EventSourceResponse

from api.models import ChatRequest
from agents.supervisor import run_agent
from api.audit_log import save_trace_to_db

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("")
async def chat_endpoint(request: Request, body: ChatRequest, background_tasks: BackgroundTasks):
    
    async def event_generator():
        trace_data = []
        async for chunk in run_agent(body.message, body.company_id, body.session_id):
            
            # Extract trace data if done
            if chunk.startswith("data: ") and "done" in chunk:
                try:
                    data = json.loads(chunk[6:])
                    if data.get("type") == "done":
                        trace_data = data.get("trace", [])
                except:
                    pass
                    
            yield chunk
            
        if trace_data:
            background_tasks.add_task(
                asyncio.to_thread,
                save_trace_to_db,
                body.company_id,
                body.session_id,
                trace_data
            )
            
    return EventSourceResponse(
        event_generator(),
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
