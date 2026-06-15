import os
import json
import sqlite3
import secrets
import uuid
import numpy as np
import faiss
from datetime import datetime
from fastembed import TextEmbedding
from shared.models import ExecutionPlan, ExecutionResult, StepStatus

MODEL_NAME = "BAAI/bge-small-en-v1.5"       # 384-dim, ~80MB, CPU-friendly
EMBED_DIM   = 384
TOP_K       = 3

DB_PATH     = os.getenv("DB_PATH",      "veda.db")
FAISS_PATH  = os.getenv("FAISS_PATH",   "veda.faiss")
ID_MAP_PATH = os.getenv("ID_MAP_PATH",  "veda_id_map.json")

class MemoryManager:
    """
    Two-layer memory:

    1. Semantic (FAISS) — vector index of past goal embeddings.
       Finds the most similar past goals in O(log n) using cosine similarity.
       Persisted to veda.faiss + veda_id_map.json.

    2. Structured (SQLite) — stores full goals, plans, results, timestamps.
       FAISS tells us WHICH past interaction is similar; SQLite gives us its
       full content once we know the row id.

    Why both? FAISS does fast semantic search but stores no metadata.
    SQLite stores everything but has no semantic search capability.
    Together: semantic retrieval with rich structured results.
    """

    def __init__(self) -> None:
        self.model = TextEmbedding(
            model_name=MODEL_NAME
        )
        self._init_db()
        self._load_faiss()

    def _init_db(self) -> None:
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL DEFAULT 'default',
                goal        TEXT    NOT NULL,
                plan_json   TEXT    NOT NULL,
                result_json TEXT,
                succeeded   INTEGER DEFAULT 0,
                created_at  TEXT    NOT NULL
            )
        """)

        # Add user_id column if the table already existed without it
        try:
            self.conn.execute("ALTER TABLE memories ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
        except sqlite3.OperationalError:
            pass  # column already exists

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                email      TEXT UNIQUE NOT NULL,
                api_key    TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        self.conn.commit()

    def _load_faiss(self) -> None:
        if os.path.exists(FAISS_PATH) and os.path.exists(ID_MAP_PATH):
            self.index  = faiss.read_index(FAISS_PATH)
            with open(ID_MAP_PATH) as f:
                self.id_map = {int(k): v for k, v in json.load(f).items()}
        else:
            self.index  = faiss.IndexFlatIP(EMBED_DIM)
            self.id_map = {}

    def _save_faiss(self) -> None:
        faiss.write_index(self.index, FAISS_PATH)
        with open(ID_MAP_PATH, "w") as f:
            json.dump(self.id_map, f)

    def _embed(self, text: str) -> np.ndarray:
        vec = np.array(list(self.model.embed([text])), dtype="float32")
        faiss.normalize_L2(vec)
        return vec

    # ── User management ────────────────────────────────────────────────

    def create_user(self, name: str, email: str) -> dict:
        """Create a new user and generate their API key."""
        user_id    = str(uuid.uuid4())
        api_key    = "veda_" + secrets.token_hex(24)
        created_at = datetime.utcnow().isoformat()

        self.conn.execute(
            "INSERT INTO users (id, name, email, api_key, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, name, email, api_key, created_at)
        )
        self.conn.commit()

        return {"id": user_id, "name": name, "email": email, "api_key": api_key, "created_at": created_at}

    def get_user_by_api_key(self, api_key: str) -> dict | None:
        """Look up a user by their API key. Returns None if not found."""
        row = self.conn.execute(
            "SELECT id, name, email, api_key, created_at FROM users WHERE api_key = ?",
            (api_key,)
        ).fetchone()
        if not row:
            return None
        return {"id": row["id"], "name": row["name"], "email": row["email"],
                "api_key": row["api_key"], "created_at": row["created_at"]}

    # ── Memory store/retrieve ──────────────────────────────────────────

    def store(
        self,
        goal:    str,
        plan:    ExecutionPlan,
        result:  ExecutionResult | None = None,
        user_id: str = "default",
    ) -> None:
        """
        Embed goal and persist to FAISS + SQLite, scoped to a user.
        Called after every execution so memory grows with real usage.
        """
        succeeded   = 0
        result_json = None

        if result is not None:
            succeeded   = 1 if result.status == StepStatus.SUCCESS else 0
            result_json = result.model_dump_json()

        cursor = self.conn.execute(
            """INSERT INTO memories (user_id, goal, plan_json, result_json, succeeded, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                goal,
                plan.model_dump_json(),
                result_json,
                succeeded,
                datetime.utcnow().isoformat(),
            ),
        )
        self.conn.commit()
        sqlite_id = cursor.lastrowid

        vec       = self._embed(goal)
        faiss_pos = self.index.ntotal
        self.index.add(vec)
        self.id_map[faiss_pos] = sqlite_id
        self._save_faiss()

    def retrieve(self, goal: str, k: int = TOP_K, user_id: str = "default") -> list[dict]:
        """
        Find k most semantically similar past goals for this user.
        FAISS search is global, then we filter by user_id at the SQLite layer.
        Returns [] if index is empty or no matches belong to this user.
        """
        if self.index.ntotal == 0:
            return []

        vec = self._embed(goal)
        # Search wider than k since we'll filter by user_id afterward
        actual_k        = min(k * 5, self.index.ntotal)
        scores, indices = self.index.search(vec, actual_k)

        results = []
        for score, faiss_pos in zip(scores[0], indices[0]):
            if faiss_pos < 0:
                continue
            sqlite_id = self.id_map.get(int(faiss_pos))
            if sqlite_id is None:
                continue
            row = self.conn.execute(
                "SELECT goal, plan_json, succeeded, created_at FROM memories WHERE id = ? AND user_id = ?",
                (sqlite_id, user_id),
            ).fetchone()
            if row:
                results.append({
                    "goal":      row["goal"],
                    "plan_json": row["plan_json"],
                    "succeeded": bool(row["succeeded"]),
                    "created_at":row["created_at"],
                    "score":     float(score),
                })
            if len(results) >= k:
                break
        return results

    def format_context(self, memories: list[dict]) -> str:
        if not memories:
            return ""

        lines = ["RELEVANT PAST EXECUTIONS (use these to inform your plan):\n"]
        for i, m in enumerate(memories, 1):
            plan   = json.loads(m["plan_json"])
            steps  = plan.get("steps", [])
            status = "✓ succeeded" if m["succeeded"] else "✗ failed"
            lines.append(f"{i}. [{status}] Goal: {m['goal']}")
            lines.append(f"   Tools used: {', '.join(s['tool'] for s in steps)}")
            lines.append(f"   Steps: {len(steps)}")
            lines.append("")

        return "\n".join(lines)