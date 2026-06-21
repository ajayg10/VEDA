import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from typing import List
from fastapi import FastAPI, HTTPException
import httpx

from fastapi import Request
from fastapi.responses import JSONResponse

from shared.models import (
    RunRequest, OrchestrationResult,
    PlanRequest, RetrieveRequest, StoreRequest,
    MemoryEntry, ExecutionPlan, ExecutionResult,
    HealthResponse, CreateUserRequest, UserResponse,
)



# Service URLs — override via .env for Docker/cloud deployments
PLANNER_URL  = os.getenv("PLANNER_URL",  "http://localhost:8001")
MEMORY_URL   = os.getenv("MEMORY_URL",   "http://localhost:8002")
EXECUTOR_URL = os.getenv("EXECUTOR_URL", "http://localhost:8003")

app = FastAPI(title="VEDA — Orchestrator", version="0.4.0")

from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

from prometheus_client import Counter, Histogram

GOALS_TOTAL    = Counter("veda_goals_total", "Total goals received")
GOALS_EXECUTED = Counter("veda_goals_executed_total", "Goals executed")
GOALS_FAILED   = Counter("veda_goals_failed_total", "Goals that failed")
PLAN_LATENCY   = Histogram("veda_plan_duration_seconds", "Plan generation time")
EXEC_LATENCY   = Histogram("veda_exec_duration_seconds", "Execution time")

API_KEY = os.getenv("VEDA_API_KEY", "")

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path in ("/health", "/register"):
        return await call_next(request)
    
    key = request.headers.get("X-API-Key", "")
    if not key:
        return JSONResponse(status_code=401, content={"error": "Missing API key"})
    
    # Validate against Memory service's user table
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{MEMORY_URL}/users/validate",
                json={"api_key": key},
                timeout=5,
            )
            data = resp.json()
            if not data.get("valid"):
                return JSONResponse(status_code=401, content={"error": "Invalid API key"})
            
            # Attach user info to request state for use in handlers
            request.state.user_id = data["user_id"]
            request.state.user_name = data["name"]
    except Exception:
        return JSONResponse(status_code=503, content={"error": "Auth service unavailable"})
    
    return await call_next(request)

def _format_context(memories: List[MemoryEntry]) -> str:
    """Convert MemoryEntry list into a prompt-ready string for the Planner."""
    if not memories:
        return ""
    lines = ["RELEVANT PAST EXECUTIONS:\n"]
    for i, m in enumerate(memories, 1):
        plan  = json.loads(m.plan_json)
        steps = plan.get("steps", [])
        status = "✓ succeeded" if m.succeeded else "✗ failed"
        lines.append(f"{i}. [{status}] Goal: {m.goal}")
        lines.append(f"   Tools used: {', '.join(s['tool'] for s in steps)}")
        lines.append(f"   Steps: {len(steps)}")
        lines.append("")
    return "\n".join(lines)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(service="orchestrator")


@app.post("/register")
async def register(req: CreateUserRequest):
    """Public endpoint — creates a new user and returns their API key."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{MEMORY_URL}/users",
                json=req.model_dump(),
            )
            if resp.status_code == 400:
                raise HTTPException(status_code=400, detail="Email already registered.")
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Registration failed.")
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Memory service unreachable.")

@app.post("/run", response_model=OrchestrationResult)
async def run(req: RunRequest, request: Request):
    user_id = request.state.user_id
    GOALS_TOTAL.inc()
   
    """
    Central workflow endpoint. Two modes:
    Mode A — plan only (request.plan is None, auto_execute=False):
      1. Retrieve similar memories from Memory service
      2. Format memory context
      3. Call Planner → get ExecutionPlan
      4. Return plan + memories (not executed)
    Mode B — execute (request.plan is provided, auto_execute=True):
      1. Call Executor with the provided plan
      2. Store result in Memory service
      3. Return plan + result
    The CLI calls Mode A first (show plan → user confirms), then Mode B.
    This separation means the plan is never regenerated during execution —
    exactly what the user approved is what gets run.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:

        # ── Mode A: Plan ──────────────────────────────────────────────────
        if req.plan is None:
            # Step 1: retrieve memories
            memories: List[MemoryEntry] = []
            try:
                resp = await client.post(
                    f"{MEMORY_URL}/retrieve",
                    json=RetrieveRequest(goal=req.goal, user_id=user_id).model_dump(),
                )
                memories = [MemoryEntry(**m) for m in resp.json().get("memories", [])]

            except Exception:
                pass   # memory failure is non-fatal — planning continues

            # Step 2: build context + call planner
            context = _format_context(memories)
            try:
                resp = await client.post(
                    f"{PLANNER_URL}/plan",
                    json=PlanRequest(
                        goal=req.goal,
                        memory_context=context,
                    ).model_dump(),
                )
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=503,
                    detail="Planner service unreachable. Is it running on port 8001?"
                )

            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Planner: {resp.text}")

            plan = ExecutionPlan(**resp.json())

            # ── Mode C: Plan + auto-execute in one shot ───────────────────
            if req.auto_execute:
                try:
                    exec_resp = await client.post(
                        f"{EXECUTOR_URL}/execute",
                        json=plan.model_dump(),
                    )
                except httpx.ConnectError:
                    raise HTTPException(status_code=503, detail="Executor service unreachable.")

                if exec_resp.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"Executor: {exec_resp.text}")

                result = ExecutionResult(**exec_resp.json())

                try:
                    await client.post(
                        f"{MEMORY_URL}/store",
                        json=StoreRequest(
                            goal=req.goal,
                            plan=plan,
                            result=result,
                            user_id=user_id,
                        ).model_dump(),
                    )
                except Exception:
                    pass

                GOALS_EXECUTED.inc()
                return OrchestrationResult(
                    goal=req.goal,
                    memories=memories,
                    plan=plan,
                    result=result,
                    executed=True,
                )

            return OrchestrationResult(
                goal=req.goal,
                memories=memories,
                plan=plan,
                executed=False,
            )

        # ── Mode B: Execute ───────────────────────────────────────────────
        if req.auto_execute and req.plan is not None:
            # Step 3: execute the exact plan the user approved
            try:
                resp = await client.post(
                    f"{EXECUTOR_URL}/execute",
                    json=req.plan.model_dump(),
                )
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=503,
                    detail="Executor service unreachable. Is it running on port 8003?"
                )

            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Executor: {resp.text}")

            result = ExecutionResult(**resp.json())

            # Step 4: persist to memory (non-fatal if it fails)
            try:
                 await client.post(
                    f"{MEMORY_URL}/store",
                    json=StoreRequest(
                        goal=req.goal,
                        plan=req.plan,
                        result=result,
                        user_id=user_id,
                    ).model_dump(),
                )
            except Exception:
                pass

            return OrchestrationResult(
                goal=req.goal,
                memories=[],   # not re-fetched in execute mode
                plan=req.plan,
                result=result,
                executed=True,
            )

        raise HTTPException(status_code=400, detail="Invalid request: provide plan + auto_execute=true, or omit plan.")