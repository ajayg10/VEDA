import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from shared.models import PlanRequest, ExecutionPlan, HealthResponse
from core.planner import Planner

# Module-level reference initialised in lifespan.
# Using a module-level var (rather than app.state) keeps the import chain
# simple — no request object needed to reach the planner instance.
_planner: Planner | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager — replaces the deprecated @app.on_event.
    Code before `yield` runs at startup; code after runs at shutdown.
    Heavy initialisation (LLM client setup, model loading) belongs here
    so it happens once per process, not once per request.
    """
    global _planner
    _planner = Planner()
    yield
    # Cleanup: nothing needed for Planner (stateless HTTP client)


app = FastAPI(title="VEDA — Planner Service", version="0.4.0", lifespan=lifespan)

from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

@app.get("/health", response_model=HealthResponse)
async def health():
    """Standard health check. Orchestrator polls this before routing requests."""
    return HealthResponse(service="planner")


@app.post("/plan", response_model=ExecutionPlan)
async def plan(request: PlanRequest):
    """
    Convert a natural language goal into a validated ExecutionPlan.
    Accepts optional memory_context injected by the Orchestrator.
    Raises 422 if the LLM fails to produce a valid plan after retries.
    """
    try:
        return await _planner.plan(request.goal, memory_context=request.memory_context)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    