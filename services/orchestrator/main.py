import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from typing import List
from fastapi import FastAPI, HTTPException
import httpx

from shared.models import (
    RunRequest, OrchestrationResult,
    PlanRequest, RetrieveRequest, StoreRequest,
    MemoryEntry, ExecutionPlan, ExecutionResult,
    HealthResponse,
)

# Service URLs — override via .env for Docker/cloud deployments
PLANNER_URL  = os.getenv("PLANNER_URL",  "http://localhost:8001")
MEMORY_URL   = os.getenv("MEMORY_URL",   "http://localhost:8002")
EXECUTOR_URL = os.getenv("EXECUTOR_URL", "http://localhost:8003")

app = FastAPI(title="VEDA — Orchestrator", version="0.4.0")


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


@app.post("/run", response_model=OrchestrationResult)
async def run(request: RunRequest):
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
        if request.plan is None:
            # Step 1: retrieve memories
            memories: List[MemoryEntry] = []
            try:
                resp = await client.post(
                    f"{MEMORY_URL}/retrieve",
                    json=RetrieveRequest(goal=request.goal).model_dump(),
                )
                memories = [MemoryEntry(**m) for m in resp.json()]
            except Exception:
                pass   # memory failure is non-fatal — planning continues

            # Step 2: build context + call planner
            context = _format_context(memories)
            try:
                resp = await client.post(
                    f"{PLANNER_URL}/plan",
                    json=PlanRequest(
                        goal=request.goal,
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
            return OrchestrationResult(
                goal=request.goal,
                memories=memories,
                plan=plan,
                executed=False,
            )

        # ── Mode B: Execute ───────────────────────────────────────────────
        if request.auto_execute and request.plan is not None:
            # Step 3: execute the exact plan the user approved
            try:
                resp = await client.post(
                    f"{EXECUTOR_URL}/execute",
                    json=request.plan.model_dump(),
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
                        goal=request.goal,
                        plan=request.plan,
                        result=result,
                    ).model_dump(),
                )
            except Exception:
                pass

            return OrchestrationResult(
                goal=request.goal,
                memories=[],   # not re-fetched in execute mode
                plan=request.plan,
                result=result,
                executed=True,
            )

        raise HTTPException(status_code=400, detail="Invalid request: provide plan + auto_execute=true, or omit plan.")