from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging

from config.settings import settings
from api.routes import chat, inventory, audit

logger = logging.getLogger("api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify Connections
    logger.info("Starting up LexAgent API...")
    try:
        q_client = settings.get_qdrant_client()
        q_client.get_collections()
        logger.info("Qdrant OK.")
    except Exception as e:
        logger.warning(f"Qdrant exception on startup: {e}")
        
    try:
        from db.connection import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        logger.info("PostgreSQL OK.")
    except Exception as e:
        logger.warning(f"PostgreSQL exception on startup: {e}")
        
    yield
    logger.info("Shutting down LexAgent API...")


app = FastAPI(
    title="LexAgent API", 
    version="1.0.0",
    lifespan=lifespan,
    root_path="/api"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/debug-path")
@app.get("/debug-path")
def debug_path(request: Request):
    return {
        "path": request.url.path,
        "root_path": request.scope.get("root_path"),
        "headers": dict(request.headers)
    }

app.include_router(chat.router)
app.include_router(inventory.router)
app.include_router(audit.router)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "services": {
            "qdrant": "unknown", # would implement active ping here
            "postgres": "unknown",
            "ollama": "unknown"
        }
    }
