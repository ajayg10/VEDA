# VEDA RFC-001: Virtual Execution & Decision Architecture

**The Agent Operating System**

> *Everything inside VEDA exists to answer one question:*
> **"Can VEDA autonomously accomplish this goal?"**
> Conversation is secondary. Execution is mandatory.

---

## 1. System Overview

VEDA is a distributed agent operating system designed for multi-step, autonomous goal execution with persistent memory, static and runtime repository analysis, LLM planning, and sandboxed action execution.

```
                  ┌──────────────────────┐
                  │       CLI / REPL     │
                  └──────────┬───────────┘
                             │ HTTP / API Key
                             ▼
                  ┌──────────────────────┐
                  │ Orchestrator Service │
                  └────┬───────────┬─────┘
                       │           │
       ┌───────────────┘           └───────────────┐
       ▼                                           ▼
┌──────────────┐                            ┌──────────────┐
│ Memory Svc   │                            │ Planner Svc  │
│ (FAISS/SQLite)                            │ (LLM Engine) │
└──────────────┘                            └──────┬───────┘
                                                   │ ExecutionPlan
                                                   ▼
                                            ┌──────────────┐
                                            │ Executor Svc │
                                            │ (Tool DAG)   │
                                            └──────┬───────┘
                                                   │
     ┌───────────────────┬─────────────────────────┼─────────────────────────┐
     ▼                   ▼                         ▼                         ▼
┌───────────┐      ┌───────────┐             ┌───────────┐             ┌───────────┐
│ Core Tools│      │ Module 8  │             │ Module 9  │             │ Module 10 │
│ (Docker/  │      │ Repository│             │ Code      │             │ Browser   │
│ Shell/HTTP│      │ Intelligence            │ Agent     │             │ Agent     │
└───────────┘      └───────────┘             └───────────┘             └───────────┘
```

---

## 2. Core Service Microservices

### 2.1 Orchestrator Service (`services/orchestrator/main.py`)
- Coordinates multi-step execution flows between Planner, Memory, and Executor.
- Mode A (Plan): Retrieves top-$k$ semantic memories for context injection, calls Planner for DAG plan generation.
- Mode B (Execute): Passes approved `ExecutionPlan` to Executor DAG engine, persists outcomes into Memory.

### 2.2 Planner Service (`services/planner/main.py`)
- LLM-powered planning engine enforcing strictly typed JSON responses.
- Encapsulates tool definitions for shell execution, python script runner, browser automation, repo intelligence, and code agent operations.
- Automatically handles retry logic and validates output schemas.

### 2.3 Memory Service (`services/memory/main.py`)
- Two-layer storage architecture:
  1. **FAISS Vector Index**: Fast cosine similarity retrieval over embedded goal strings (`BAAI/bge-small-en-v1.5`).
  2. **SQLite Relational Database**: Persistent storage for detailed interaction records, execution graphs, user authorization, and execution outcomes.

### 2.4 Executor Service (`services/executor/main.py`)
- Dependency graph sorting (Topological Sort) and step dispatcher.
- Sandboxed isolated workspace execution with Docker container isolation (`python:3.11-alpine`) for untrusted Python scripts and shell commands.

---

## 3. Core Modules (Modules 8, 9, 10)

### Module 8 — Repository Intelligence (`core/project/`)
Provides static analysis over source code bases without executing code:
- **Scanner & Detectors**: Multi-language detection (Python, JS/TS, Go, Java, Rust, Ruby, PHP) and framework signals (FastAPI, Django, Flask, React, Next.js, Spring, etc.).
- **Dependency Graph**: AST relative and absolute import analysis.
- **Context Selection & Token Budgeting**: Lexical and structural scoring for selecting optimal files within LLM token constraints.
- **Architecture Summarizer**: Markdown and prompt-formatted structural summaries.

### Module 9 — Code Agent (`core/code_agent/`)
Provides deterministic and safe file manipulation and code processing:
- **Repository Reader & Editor**: Atomic multi-file writes with path traversal guards.
- **Unified Patch Applier**: Context-aware patch header parsing and application.
- **Python Symbol Renamer**: Tokenizer-level identifier replacement (safely ignoring comments and strings).
- **Code Reviewer**: Static safety & style checks (bare-except, mutable defaults, production asserts, print statements, missing annotations).
- **Scaffold & Documentation Generators**: AST-based documentation extraction and signature-aware unittest generation.

### Module 10 — Browser Agent (`core/browser_agent/`)
Provides browser automation:
- Playwright Chromium context manager with snapshot capture (`PageSnapshot`).
- Rich interactive steps: navigation, selector click, form typing/filling, login helpers, text & link scraping, full-page screenshot/PDF exports, element waiting, and CAPTCHA detection.

---

## 4. Architectural Rules & Contribution Guidelines

Every new PR or feature added to VEDA must answer three mandatory questions:

1. **Which module does it belong to?** (e.g. Core System, Module 8, Module 9, Module 10, etc.)
2. **Which roadmap checkbox(es) does it complete?** (Refer to `docs/ROADMAP.md`)
3. **Does it strengthen the runtime or add a new capability?**
