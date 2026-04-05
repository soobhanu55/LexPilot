import time
from datetime import datetime
from agents.state import LexAgentState
from db.queries import get_inventory
import asyncio

DEADLINES = [
    {"milestone": "Prohibited AI practices ban", "date": "2025-02-02", "articles": ["Article 5"], "tier": "prohibited"},
    {"milestone": "GPAI model obligations", "date": "2025-08-02", "articles": ["Articles 51-56"], "tier": "gpai"},
    {"milestone": "Full Act enforcement (most provisions)", "date": "2026-08-02", "articles": ["All"], "tier": "all"},
    {"milestone": "High-risk systems (Annex III)", "date": "2027-12-02", "articles": ["Article 6", "Annex III"], "tier": "high-risk"},
    {"milestone": "High-risk systems (Annex I)", "date": "2028-08-02", "articles": ["Annex I"], "tier": "high-risk-annex-i"},
]

async def track_deadlines(state: LexAgentState) -> LexAgentState:
    start_t = time.time()
    
    try:
        inventory = await asyncio.to_thread(get_inventory, state["company_id"])
        
        deadline_info = []
        today = datetime.now()
        
        for sys in inventory:
            tier = sys["risk_tier"]
            matched_dl = None
            
            if tier == "prohibited":
                matched_dl = DEADLINES[0]
            elif tier == "high-risk":
                # Simplification: assume Annex III unless specified
                matched_dl = DEADLINES[3]
            elif tier in ["limited-risk", "minimal-risk"]:
                matched_dl = DEADLINES[2]
            else:
                matched_dl = DEADLINES[2]
                
            dl_date = datetime.strptime(matched_dl["date"], "%Y-%m-%d")
            days_rem = (dl_date - today).days
            
            urgency = "low"
            if days_rem < 0:
                urgency = "critical" # Overdue
            elif days_rem < 90:
                urgency = "critical"
            elif days_rem < 180:
                urgency = "high"
            elif days_rem < 365:
                urgency = "medium"
                
            deadline_info.append({
                "system": sys["system_name"],
                "deadline": matched_dl["date"],
                "days_remaining": days_rem,
                "urgency": urgency
            })
            
        state["deadline_info"] = deadline_info
        
    except Exception as e:
        state["error"] = f"Deadlines failed: {e}"

    latency = int((time.time() - start_t) * 1000)
    trace = state.get("agent_trace", [])
    trace.append({
        "agent": "deadlines",
        "action": "calculate",
        "input": {"company_id": state["company_id"]},
        "output": {"tracked_systems": len(state.get("deadline_info", []))},
        "latency_ms": latency
    })
    state["agent_trace"] = trace
    
    return state
