"""FastAPI application entry point with middleware and route registration."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.routes import (
    admin_routes,
    auth_routes,
    compute_routes,
    llm_routes,
    participant_routes,
    problem_routes,
    ws_routes,
)
from app.storage.store import storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize storage and other startup tasks."""
    await storage.initialize()
    yield


app = FastAPI(
    title="Scenario Planning Studio",
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS ---
origins = [settings.APP_URL]
if settings.APP_ENV == "development":
    origins.append("http://localhost:8000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate Limiting ---
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Static Files & Templates ---
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "web" / "static"
TEMPLATE_DIR = BASE_DIR / "web" / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# --- Routes ---
app.include_router(auth_routes.router)
app.include_router(problem_routes.router)
app.include_router(participant_routes.router)
app.include_router(compute_routes.router)
app.include_router(admin_routes.router)
app.include_router(llm_routes.router)
app.include_router(ws_routes.router)


# --- Health Check ---
@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok"}


# --- Global Error Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
