import json
import time
from agents.state import LexAgentState
from config.settings import settings
from db.queries import upsert_ai_system, get_inventory, update_compliance_status
import asyncio

async def manage_inventory(state: LexAgentState) -> LexAgentState:
    start_t = time.time()
    llm = settings.get_llm()
    
    prompt = f"""You must respond with ONLY valid JSON. No explanation, no markdown, no preamble.
Schema: {{"action": "add|list|update|delete|unknown", "system_name": "string", "description": "string", "status": "string"}}

Analyze the user's message to determine if they want to manage their AI inventory.
User: {state['user_message']}
"""

    try:
        response = llm.invoke(prompt)
        res_text = response.content.strip()
        if res_text.startswith("```json"):
            res_text = res_text[7:-3]
        elif res_text.startswith("```"):
            res_text = res_text[3:-3]
            
        action_data = json.loads(res_text.strip())
        action = action_data.get("action", "unknown")
        
        state["inventory_action"] = action_data
        
        # Execute action using Threaded connection via asyncio
        if action == "list":
            items = await asyncio.to_thread(get_inventory, state["company_id"])
            answer = "Here is your current AI System Inventory:\n"
            for i in items:
                answer += f"- **{i['system_name']}** ({i['risk_tier']}): {i['description']} (Status: {i['compliance_status']})\n"
            state["final_answer"] = answer
            state["inventory_action"]["result"] = items
            
        elif action == "add":
            # For pure add we assume classification ran or will run. We just mock a tier if not set.
            tier = state.get("classification_result", {}).get("tier", "unknown")
            articles = state.get("classification_result", {}).get("articles", [])
            
            sys = await asyncio.to_thread(
                upsert_ai_system, 
                state["company_id"], 
                action_data.get("system_name", "Unknown System"),
                action_data.get("description", "No description"),
                tier,
                articles
            )
            state["final_answer"] = f"Added **{sys['system_name']}** to inventory with Risk Tier: **{tier}**."
            state["inventory_action"]["result"] = sys
            
        else:
            state["final_answer"] = "Inventory action not fully supported in this flow, try using the Dashboard UI."
            
    except Exception as e:
        state["error"] = f"Memory agent failed: {e}"
        state["final_answer"] = "Could not process inventory request."

    latency = int((time.time() - start_t) * 1000)
    trace = state.get("agent_trace", [])
    trace.append({
        "agent": "memory",
        "action": state.get("inventory_action", {}).get("action", "unknown"),
        "input": {"message": state["user_message"]},
        "output": {"status": "success"},
        "latency_ms": latency
    })
    state["agent_trace"] = trace
    
    return state
