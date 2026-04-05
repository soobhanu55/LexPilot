from functools import wraps
from fastapi import Request
from db.queries import log_agent_action
import time
import asyncio
import json

# EU AI Act Article 12 requires record-keeping and logging for high-risk systems.
# We ensure the agent logs its own internal traces natively to meet these guidelines
# in the platform itself providing 100% auditable history stored totally locally without 3rd party APIs.

def save_trace_to_db(company_id: str, session_id: str, trace_list: list):
    for trace in trace_list:
        log_agent_action(
            company_id=company_id,
            session_id=session_id,
            agent_name=trace.get("agent", "unknown"),
            action=trace.get("action", "unknown"),
            input_data=trace.get("input", {}),
            output_data=trace.get("output", {}),
            latency_ms=trace.get("latency_ms", 0)
        )
