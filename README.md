# VEDA

Virtual Execution & Decision Architecture

An AI-powered execution system that converts natural language goals into structured workflows using LLM planning, dependency-aware execution, semantic memory retrieval, and automated tool orchestration.

## Features

- LLM-powered planning
- Dependency-aware execution engine
- Semantic memory using FAISS
- SQLite persistence
- Provider abstraction (Groq/Ollama)
- Tool execution framework
- Confirmation gates for destructive operations

## Architecture

User Goal
↓
Planner
↓
Execution Plan
↓
Executor
↓
Memory

## Roadmap

- [x] Planner
- [x] Execution Engine
- [x] Memory Layer
- [ ] FastAPI Microservices
- [ ] Docker & Compose
- [ ] Nginx & Auth
- [ ] CI/CD
- [ ] Cloud Deployment
