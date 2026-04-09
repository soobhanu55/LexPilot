from fastapi import APIRouter
from fastapi.responses import JSONResponse
from db.queries import get_audit_log

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("/{company_id}")
def list_audit_trail(company_id: str, limit: int = 50):
    logs = get_audit_log(company_id, limit)
    return logs

@router.get("/{company_id}/export")
def export_audit_trail(company_id: str):
    logs = get_audit_log(company_id, limit=1000)
    return JSONResponse(content=logs, headers={"Content-Disposition": f"attachment; filename=audit_{company_id}.json"})
