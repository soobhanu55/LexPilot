from fastapi import APIRouter, HTTPException
from api.models import InventoryItem
from db.queries import get_inventory, upsert_ai_system, update_compliance_status

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.get("/{company_id}", response_model=list[InventoryItem])
def list_inventory(company_id: str):
    items = get_inventory(company_id)
    return items

@router.post("/{company_id}")
def add_system(company_id: str, system_name: str, description: str):
    # Standard endpoint adds as pending classification via simple post
    from db.queries import create_company, get_company
    if not get_company(company_id):
        try:
            create_company(company_id)
        except:
            pass # Maybe UUID exists but we use names
    
    sys = upsert_ai_system(company_id, system_name, description, "unknown", [])
    return sys

@router.patch("/{company_id}/{system_id}")
def set_status(company_id: str, system_id: str, status: str):
    res = update_compliance_status(system_id, status)
    if not res:
        raise HTTPException(status_code=404, detail="System not found")
    return res

@router.delete("/{company_id}/{system_id}")
def delete_system(company_id: str, system_id: str):
    res = update_compliance_status(system_id, "decommissioned")
    return res

@router.get("/{company_id}/deadlines")
def get_deadlines(company_id: str):
    # Dummy integration since actual deadlines computed via agent normally
    return {"status": "Use Agent to track accurate deadlines"}
