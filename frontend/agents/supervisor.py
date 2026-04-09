import json
import time
from typing import AsyncGenerator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.state import LexAgentState
from agents.classifier import classify_ai_system
from agents.retriever import retrieve_articles
from agents.checklist import generate_checklist
from agents.memory_agent import manage_inventory
from agents.deadlines import track_deadlines
from config.settings import settings

# 1. Intent Detection
async def detect_intent(state: LexAgentState) -> LexAgentState:
    llm = settings.get_llm()
    prompt = f"""You must respond with ONLY valid JSON. No explanation, no markdown.
Schema: {{"intent": "classify|question|checklist|inventory|deadlines"}}

Determine the user's intent:
- classify: User wants to know the risk tier of an AI system.
- question: User asks a general question about the EU AI Act.
- checklist: User wants compliance steps for their AI system.
- inventory: User wants to add, list, or update their AI systems.
- deadlines: User asks about enforcement dates.

User: {state['user_message']}"""

    try:
        resp = llm.invoke(prompt)
        res_text = resp.content.strip()
        if res_text.startswith("```json"): res_text = res_text[7:-3]
        elif res_text.startswith("```"): res_text = res_text[3:-3]
        data = json.loads(res_text.strip())
        state["intent"] = data.get("intent", "question")
    except:
        state["intent"] = "question"
        
    if "agent_trace" not in state: state["agent_trace"] = []
    
    return state

# 2. Routing logic
def route_to_agent(state: LexAgentState):
    intent = state.get("intent", "question")
    if intent == "classify": return "classifier_node"
    if intent == "question": return "retriever_node"
    if intent == "checklist": return "checklist_node"
    if intent == "inventory": return "memory_node"
    if intent == "deadlines": return "deadlines_node"
    return "retriever_node"

# 3. Synthesizer node (dummy for graph building, actual streaming handled externally)
async def synthesize_answer(state: LexAgentState) -> LexAgentState:
    # Final state processing if needed, streaming happens in run_agent
    return state

# Build Graph
builder = StateGraph(LexAgentState)

builder.add_node("detect_intent", detect_intent)
builder.add_node("classifier_node", classify_ai_system)
builder.add_node("retriever_node", retrieve_articles)
builder.add_node("checklist_node", generate_checklist)
builder.add_node("memory_node", manage_inventory)
builder.add_node("deadlines_node", track_deadlines)
builder.add_node("synthesize_answer", synthesize_answer)

builder.set_entry_point("detect_intent")
builder.add_conditional_edges("detect_intent", route_to_agent)

for n in ["classifier_node", "retriever_node", "checklist_node", "memory_node", "deadlines_node"]:
    builder.add_edge(n, "synthesize_answer")
    
builder.add_edge("synthesize_answer", END)

memory_saver = MemorySaver()
graph = builder.compile(checkpointer=memory_saver)

async def run_agent(user_message: str, company_id: str, session_id: str) -> AsyncGenerator[str, None]:
    
    thread_config = {"configurable": {"thread_id": session_id}}
    
    # We pass minimal state; MemorySaver handles the rest
    initial_state = {
        "user_message": user_message,
        "company_id": company_id,
        "session_id": session_id,
        "agent_trace": [],
        "citations": [],
        "retrieved_articles": []
    }
    
    # Run graph until synthesize
    state_generator = graph.astream(initial_state, thread_config)
    
    final_state = initial_state
    async for event in state_generator:
        for k, v in event.items():
            final_state.update(v)
            
    # Now Synthesize and Stream Final Answer
    intent = final_state.get("intent")
    sys_prompt = "You are LexAgent, an expert EU AI Act compliance assistant. Respond accurately based on the provided context."
    context_str = f"Intent: {intent}\n"
    
    citations = set()
    
    if intent == "classify":
        cls = final_state.get("classification_result", {})
        context_str += f"Classification: {cls}\n"
        citations.update(cls.get("articles", []))
    elif intent == "question":
        retrieved = final_state.get("retrieved_articles", [])
        context_str += "Retrieved Articles:\n"
        for i, a in enumerate(retrieved):
            context_str += f"- {a['article_id']}: {a['title']} - {a['text'][:500]}...\n"
            citations.add(a["article_id"])
    elif intent == "inventory":
        context_str += f"Inventory Action Result: {final_state.get('final_answer')}\n"
    elif intent == "deadlines":
        context_str += f"Deadline Info: {final_state.get('deadline_info')}\n"
    elif intent == "checklist":
        checklist = final_state.get("checklist", [])
        context_str += f"Checklist Generated: {len(checklist)} items.\n"
        for i in checklist: citations.add(i["article"])
        
    prompt = f"{sys_prompt}\n\nContext:\n{context_str}\n\nUser Q: {user_message}\n\nProvide the final response. Cite securely using [Article X] inline."
    
    llm = settings.get_llm(streaming=True)
    
    yield f"data: {json.dumps({'type': 'citations', 'articles': list(citations)})}\n\n"
    
    try:
        response_stream = llm.astream(prompt)
        async for chunk in response_stream:
            yield f"data: {json.dumps({'type': 'answer', 'text': chunk.content})}\n\n"
            
    except Exception as e:
        yield f"data: {json.dumps({'type': 'answer', 'text': f' Error generating response: {e}'})}\n\n"
    
    # Final Done Output with internal structures to save to db
    latency_fake = sum([t["latency_ms"] for t in final_state.get("agent_trace", [])])
    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'latency_ms': latency_fake, 'trace': final_state.get('agent_trace', [])})}\n\n"
