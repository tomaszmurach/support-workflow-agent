# AI Support Workflow Agent

> Portfolio project — **Support Copilot** for e-commerce operators. **Status: M0 architecture draft; implementation not started.**

A Python backend where a support operator requests an AI-assisted analysis of a customer ticket. The agent can read a ticket-scoped order, retrieve store policies, and draft a grounded reply. Escalation is a **proposal**, not an automatic write: a human must approve it, and the backend re-checks business rules before making the change.

## What makes this more than a chatbot?

- Controlled tool/function calling against application services, not arbitrary SQL.
- Typed and validated AI outputs with traceable evidence references.
- Human approval, business-state validation, transactionality and an audit trail.
- Repeatable evaluations for both agent behavior and safety boundaries.

## Proposed stack

Python, FastAPI, Pydantic, async SQLAlchemy, Alembic, PostgreSQL, pgvector, OpenAI API, pytest, Docker Compose and GitHub Actions. Start with the provider SDK; evaluate LangGraph for orchestration when stateful workflows justify it. A lightweight operator UI comes after the backend vertical slice.

## Design documents

- [Product requirements](docs/PRD.md) — original v0.1 draft (preserved unchanged)
- [Architecture](docs/architecture.md) — components and runtime flows
- [Domain model & tool contracts](docs/domain-model.md) — entities, states, tools and trust boundaries
- [REST API contracts](docs/api-contracts.md) — proposed endpoints and error semantics
- [Acceptance criteria](docs/acceptance-criteria.md) — definition of done and test scenarios
- [Initial backlog](docs/backlog.md) — implementation order
- [Architecture decisions](docs/decisions/) — ADRs, all initially *proposed*

## Development status


## Local Development

### Requirements

- Python 3.13
- Git

### Setup (Windows / PowerShell)

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

### Run the API

```powershell
python -m uvicorn support_workflow_agent.main:app --reload
```

- Health endpoint: http://127.0.0.1:8000/health
- Swagger UI: http://127.0.0.1:8000/docs

### Run checks

```powershell
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
```

