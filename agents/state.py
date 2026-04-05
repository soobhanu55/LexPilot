from typing import TypedDict

class LexAgentState(TypedDict):
    # Input
    user_message: str
    company_id: str
    session_id: str

    # Routing
    intent: str  # "classify" | "question" | "checklist" | "inventory" | "deadlines"
    
    # Intermediate
    retrieved_articles: list[dict]    # [{article_id, title, text, score}]
    graph_neighbors: list[str]        # article IDs from graph traversal
    classification_result: dict       # {tier, articles, reasoning}
    checklist: list[dict]             # [{obligation, article, status, deadline}]
    inventory_action: dict            # {action, system_name, ...}
    deadline_info: list[dict]         # [{system, deadline, days_remaining, urgency}]

    # Output
    final_answer: str
    citations: list[str]
    agent_trace: list[dict]           # [{agent, action, input, output, latency_ms}]
    
    # Control
    error: str | None
    iteration_count: int
