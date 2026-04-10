import json
import time
from agents.state import LexAgentState
from config.settings import settings

async def classify_ai_system(state: LexAgentState) -> LexAgentState:
    start_t = time.time()
    llm = settings.get_llm()
    
    prompt = f"""You must respond with ONLY valid JSON. No explanation, no markdown, no preamble.
Schema: {{"tier": "prohibited|high-risk|limited-risk|minimal-risk", "matched_article": "Article X", "matched_annex_entry": "string or null", "reasoning": "string", "confidence": "high|medium|low"}}

You are analyzing an AI system to classify it under the EU AI Act.
Rules:
1. Prohibited (Article 5): Social scoring, real-time remote biometric id in public, cognitive behavioral manipulation, untargeted facial recognition scraping, emotion inference in workplace/education, biometric categorization based on sensitive traits (political/religious/sexual), predictive policing.
2. High-Risk (Annex III): 
   - Biometric identification and categorisation
   - Critical infrastructure management
   - Education and vocational training
   - Employment, HR, and access to self-employment
   - Access to essential private/public services
   - Law enforcement
   - Migration, asylum, border control
   - Justice and democratic processes
   ALSO: Safety component of a product under Annex I (machinery, medical devices, aviation, toys, etc.).
3. Limited-Risk: Chatbot, emotion recognition (outside workplace/ed), deep fakes (with disclosure), general-purpose AI.
4. Minimal-Risk: Everything else (e.g. spam filters, video games, inventory management).

User Description: {state['user_message']}
"""

    try:
        response = await llm.ainvoke(prompt)
        res_text = response.content.strip()
        # Clean up any potential markdown backticks
        if res_text.startswith("```json"):
            res_text = res_text[7:-3]
        elif res_text.startswith("```"):
            res_text = res_text[3:-3]
            
        result = json.loads(res_text.strip())
        state["classification_result"] = {
            "tier": result.get("tier", "minimal-risk"),
            "articles": [result.get("matched_article", "N/A")],
            "reasoning": result.get("reasoning", "No reasoning provided.")
        }
        
    except Exception as e:
        state["error"] = f"Classification failed: {e}"
        state["classification_result"] = {"tier": "unknown", "articles": [], "reasoning": str(e)}

    latency = int((time.time() - start_t) * 1000)
    trace = state.get("agent_trace", [])
    trace.append({
        "agent": "classifier",
        "action": "classify",
        "input": {"message": state["user_message"]},
        "output": state["classification_result"],
        "latency_ms": latency
    })
    state["agent_trace"] = trace

    return state
