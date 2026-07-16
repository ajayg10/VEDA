# VEDA Roadmap (v1.0 → v5.0 Blueprint)

Master development roadmap tracking completed and planned capabilities across all VEDA subsystems.

---

## 0. Project Foundation
- [x] Vision document & Architecture specification (`docs/ARCHITECTURE.md`)
- [x] Master Roadmap (`docs/ROADMAP.md`)
- [x] Microservice architecture & Docker compose specification
- [x] Pydantic models & RPC schema contracts

---

## 1. Interface Layer
- [x] Rich Interactive REPL CLI (`cli/main.py`)
- [x] Colorized Execution Plan rendering & status panels
- [x] Multi-service health monitoring checks
- [x] Command autocomplete & command dispatch helper (`analyze <path>`)
- [ ] Web User Interface & Dashboard

---

## 2. Core Execution Engine & Memory
- [x] Microservice Orchestration (FastAPI DAG executor)
- [x] Two-Layer Memory Architecture (FAISS Semantic Index + SQLite Persistence)
- [x] Multitenancy user key authentication & memory isolation
- [x] Sandboxed Docker container runner (`python:3.11-alpine`)
- [x] Topological sort execution graph with dependency tracking

---

## 8. Module 8 — Repository Intelligence
- [x] Language & Framework detection engine
- [x] AST-based Python import dependency graph builder
- [x] Entrypoint discovery (Python `__main__`, Go `main()`, JS scripts)
- [x] Structural folder tree visualization (`FolderNode`)
- [x] Lexical context selector & Token Budgeter for LLM prompts
- [x] Architecture Summarizer & Rich CLI renderer
- [x] Planner tool registration (`project_scan`, `project_context`)

---

## 9. Module 9 — Code Agent
- [x] Path-traversal safe Repository Reader & Atomic Editor
- [x] Unified Diff generator & Context-aware Patch Applier
- [x] Token-level Python identifier Renamer
- [x] Static AST Code Reviewer (6 detection rules)
- [x] AST Documentation generator
- [x] Signature-aware Unittest scaffold generator
- [x] Planner tool registration (`code_read`, `code_edit`, `code_patch`, `code_review`, `code_rename`, `code_docs`, `code_diff`, `code_gen_tests`)

---

## 10. Module 10 — Browser Agent
- [x] Playwright Chromium session wrapper
- [x] Page snapshotting & navigation handling
- [x] Dynamic web interaction (Click, Type, Form Fill, Login automation)
- [x] Element scraping (Text & Link extraction)
- [x] Screenshot, PDF export, & File download actions
- [x] Planner auto-routing for web requests (`browser_action`)
