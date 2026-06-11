import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.models import ExecutionPlan, ExecutionResult, HealthResponse
from core.executor import Executor

_executor: Executor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _executor
    _executor = Executor()
    yield


app = FastAPI(title="VEDA — Executor Service", version="0.4.0", lifespan=lifespan)

from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(service="executor")


@app.post("/execute", response_model=ExecutionResult)
async def execute(plan: ExecutionPlan):
    """
    Run an ExecutionPlan through the tool dispatch engine.
    Accepts the full plan as the request body — FastAPI deserialises
    it directly into the Pydantic model, so no manual parsing needed.
    """
    return await _executor.execute(plan)