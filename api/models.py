from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    company_id: str
    session_id: str

class InventoryItem(BaseModel):
    id: str
    system_name: str
    description: str
    risk_tier: str
    classification_articles: list[str]
    compliance_status: str
    created_at: str
    updated_at: str

class AuditEntry(BaseModel):
    id: str
    agent_name: str
    action: str
    latency_ms: int
    created_at: str

class CompanyCreate(BaseModel):
    name: str

class ComplianceChecklistItem(BaseModel):
    obligation: str
    article: str
    description: str
    deadline: str
    status: str
    urgency: str
