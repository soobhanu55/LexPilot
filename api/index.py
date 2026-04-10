import sys
import os
import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure the root directory is in the python path for Vercel
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from config.settings import settings
from api.routes import chat, inventory, audit

logger = logging.getLogger("api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up LexAgent API (v1.0.2-diag)...")
    yield
    logger.info("Shutting down LexAgent API...")

app = FastAPI(
    title="LexAgent API", 
    version="1.0.2-diag",
    lifespan=lifespan
)

# Global Error Handler to catch 500s and return JSON instead of Next.js HTML
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Unhandled Exception: {error_details}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "type": type(exc).__name__,
            "trace": error_details if settings.debug else "Detailed trace disabled in production"
        }
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
