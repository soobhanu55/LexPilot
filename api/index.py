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
    # Skipping heavy connection checks on startup to avoid Vercel timeouts
    # These will be verified on-demand during agent execution.
    yield
    logger.info("Shutting down LexAgent API...")


app = FastAPI(
    title="LexAgent API", 
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
@app.get("/api")
@app.get("/api/health-check")
def simple_health_check():
    return {"status": "ok", "message": "LexAgent API is alive"}

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

# Diagnostic: Include routers both with and without /api prefix
# This makes routing work regardless of whether Vercel strips the prefix
app.include_router(chat.router)
app.include_router(chat.router, prefix="/api")

app.include_router(inventory.router)
app.include_router(inventory.router, prefix="/api")

app.include_router(audit.router)
app.include_router(audit.router, prefix="/api")

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
