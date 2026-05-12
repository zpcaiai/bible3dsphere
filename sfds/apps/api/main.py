"""
SFDS v3 — FastAPI Entry Point

Acts as the orchestration gateway only.
Does NOT contain business logic — delegates to services.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.config.settings import settings
from apps.api.routers import (
    decision_router,
    formation_router,
    graph_router,
    time_router,
    vector_router,
    health_router,
    system_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all service connections on startup."""
    from packages.config.connections import init_connections, close_connections
    await init_connections()
    yield
    await close_connections()


app = FastAPI(
    title="SFDS v3 — Human Formation Intelligence System",
    description=(
        "A structural mirror of human inner dynamics over time. "
        "NOT a judgment system. NOT a diagnosis tool. "
        "A reflective architecture for pattern awareness and formation support."
    ),
    version="3.8.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route registration ────────────────────────────────────────
app.include_router(health_router,    prefix="/api/health",            tags=["health"])
app.include_router(decision_router,  prefix="/api/sfds/v2/decision",  tags=["decision"])
app.include_router(formation_router, prefix="/api/sfds/v3/formation", tags=["formation"])
app.include_router(graph_router,     prefix="/api/sfds/v2/graph",     tags=["graph"])
app.include_router(time_router,      prefix="/api/sfds/v2/time",      tags=["timeseries"])
app.include_router(vector_router,    prefix="/api/sfds/v2/vector",    tags=["vector"])
app.include_router(system_router,    prefix="/api/sfds/v3/system",    tags=["system"])


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
