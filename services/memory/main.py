import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, HTTPException

from shared.models import (
    RetrieveRequest, StoreRequest,
    MemoryEntry, HealthResponse, ValidateKeyResponse,
    CreateUserRequest, UserResponse, ValidateKeyRequest,
)
from core.memory import MemoryManager

_memory: MemoryManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _memory
    # MemoryManager downloads the embedding model on first run (~80MB),
    # then loads it from HuggingFace cache. Subsequent startups are fast.
    _memory = MemoryManager()
    yield


app = FastAPI(title="VEDA — Memory Service", version="0.4.0", lifespan=lifespan)

from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(service="memory")


@app.post("/retrieve", response_model=List[MemoryEntry])
async def retrieve(request: RetrieveRequest):
    """
    Embed the goal, search FAISS for the k most similar past goals,
    and return their metadata from SQLite.
    Returns an empty list if the index is empty.
    """
    raw = _memory.retrieve(request.goal, k=request.k)
    return [MemoryEntry(**m) for m in raw]


@app.post("/store", status_code=204)
async def store(request: StoreRequest):
    """
    Embed and persist the goal + plan + result.
    Returns 204 No Content — the caller doesn't need a response body.
    Failures here should never crash the caller (Orchestrator wraps in try/except).
    """
    _memory.store(request.goal, request.plan, request.result)
    
@app.post("/users", response_model=UserResponse)
async def create_user(req: CreateUserRequest):
    try:
        user = _memory.create_user(req.name, req.email)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return UserResponse(**user)

@app.post("/users/validate", response_model=ValidateKeyResponse)
async def validate_key(req: ValidateKeyRequest):
    user = _memory.get_user_by_api_key(req.api_key)
    if not user:
        return ValidateKeyResponse(valid=False)
    return ValidateKeyResponse(valid=True, user_id=user["id"], name=user["name"])    