import json
from psycopg2.extras import RealDictCursor
from db.connection import get_conn

def create_company(name: str) -> dict:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO companies (name) VALUES (%s) RETURNING *",
                (name,)
            )
            return dict(cur.fetchone())

def get_company(company_id: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM companies WHERE id = %s", (company_id,))
            res = cur.fetchone()
            return dict(res) if res else None

def upsert_ai_system(company_id: str, system_name: str, description: str, risk_tier: str, articles: list[str]) -> dict:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO ai_inventory (company_id, system_name, description, risk_tier, classification_articles)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (company_id, system_name, description, risk_tier, articles)
            )
            return dict(cur.fetchone())

def get_inventory(company_id: str) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM ai_inventory WHERE company_id = %s ORDER BY created_at DESC", (company_id,))
            return [dict(row) for row in cur.fetchall()]

def update_compliance_status(system_id: str, status: str) -> dict:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "UPDATE ai_inventory SET compliance_status = %s WHERE id = %s RETURNING *",
                (status, system_id)
            )
            return dict(cur.fetchone())

def log_agent_action(company_id: str, session_id: str, agent_name: str, action: str, input_data: dict, output_data: dict, latency_ms: int) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_log (company_id, session_id, agent_name, action, input, output, latency_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (company_id, session_id, agent_name, action, json.dumps(input_data), json.dumps(output_data), latency_ms)
            )

def get_audit_log(company_id: str, limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM audit_log WHERE company_id = %s ORDER BY created_at DESC LIMIT %s",
                (company_id, limit)
            )
            return [dict(row) for row in cur.fetchall()]
