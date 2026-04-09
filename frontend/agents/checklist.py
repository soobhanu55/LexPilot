import time
from agents.state import LexAgentState

async def generate_checklist(state: LexAgentState) -> LexAgentState:
    start_t = time.time()
    
    # Fallback to minimal if missing
    tier = state.get("classification_result", {}).get("tier", "minimal-risk")
    checklist = []
    
    if tier == "prohibited":
        checklist = [{
            "obligation": "This AI system is prohibited under Article 5. Immediate decommissioning required.",
            "article": "Article 5",
            "description": "Stop usage, dismantle the system.",
            "deadline": "Immediate",
            "status": "pending",
            "urgency": "critical"
        }]
    elif tier == "high-risk":
        checklist = [
            {"obligation": "Risk management system", "article": "Article 9", "description": "Establish, implement, document and maintain a risk management system.", "deadline": "Before placing on market", "status": "pending", "urgency": "high"},
            {"obligation": "Data and data governance", "article": "Article 10", "description": "Training, validation and testing data sets shall be subject to appropriate data governance.", "deadline": "Before development completion", "status": "pending", "urgency": "high"},
            {"obligation": "Technical documentation", "article": "Article 11", "description": "Draw up technical documentation and keep it up to date.", "deadline": "Before placing on market", "status": "pending", "urgency": "medium"},
            {"obligation": "Record-keeping", "article": "Article 12", "description": "Automatic recording of events ('logs') over the lifetime of the system.", "deadline": "Implementation phase", "status": "pending", "urgency": "medium"},
            {"obligation": "Transparency and provision of info", "article": "Article 13", "description": "Ensure operation is transparent for users to interpret output.", "deadline": "Before placing on market", "status": "pending", "urgency": "medium"},
            {"obligation": "Human oversight", "article": "Article 14", "description": "Built so it can be effectively overseen by natural persons.", "deadline": "Design phase", "status": "pending", "urgency": "high"},
            {"obligation": "Accuracy, robustness and cybersecurity", "article": "Article 15", "description": "Perform consistently, resilient to errors, faults and attacks.", "deadline": "Continuous", "status": "pending", "urgency": "high"},
            {"obligation": "Quality management system", "article": "Article 17", "description": "Put a QMS in place ensuring compliance.", "deadline": "Pre-market", "status": "pending", "urgency": "medium"}
        ]
    elif tier == "limited-risk":
        checklist = [{
            "obligation": "Transparency obligations", "article": "Article 52", 
            "description": "Inform natural persons they are interacting with an AI system.", 
            "deadline": "Deploy time", "status": "pending", "urgency": "medium"
        }]
    else: # minimal-risk
        checklist = [{
            "obligation": "Voluntary code of conduct", "article": "Article 69", 
            "description": "Consider applying voluntary codes of conduct.", 
            "deadline": "Optional", "status": "pending", "urgency": "low"
        }]
        
    state["checklist"] = checklist
    
    latency = int((time.time() - start_t) * 1000)
    trace = state.get("agent_trace", [])
    trace.append({
        "agent": "checklist",
        "action": "generate",
        "input": {"tier": tier},
        "output": {"checklist_items": len(checklist)},
        "latency_ms": latency
    })
    state["agent_trace"] = trace
    
    return state
