# AI Support Workflow Agent

> Portfolio project — **Support Copilot** for e-commerce operators.
> **Status: M1 foundations in progress; FastAPI skeleton and local PostgreSQL available.**

The planned Python backend will let a support operator request an AI-assisted analysis of a customer ticket. The agent will read a ticket-scoped order, retrieve store policies, and draft a grounded reply. Escalation will require a **proposal**, human approval, and backend business-rule checks before any change.

## Planned capabilities

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

- **Implemented:** Python 3.13 package setup, FastAPI application with a typed `GET /health` endpoint, pytest/Ruff configuration, and local PostgreSQL 17 with pgvector managed by Docker Compose.
- **Next (remaining M1 foundations):** SQLAlchemy models, Alembic migrations, synthetic fixtures, and GitHub Actions quality gates.
- **Planned (M2–M5):** Ticket/order services, LLM tool calling, persisted analyses, knowledge retrieval, human approval workflows, evaluations, and an operator UI.


## Local Development

### Local PostgreSQL

The development database runs in Docker Compose
using PostgreSQL 17 with pgvector.

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Set a local password in `.env`.

Start PostgreSQL:

```powershell
docker compose up -d db
docker compose ps
```

The database is available at `127.0.0.1:5433`.

Connect using psql:

```powershell
docker compose exec db psql -U support_agent -d support_workflow
```

Stop and remove containers without deleting database data:

```powershell
docker compose down
```

Database files are persisted in the `postgres_data`
Docker named volume.


### Requirements

- Python 3.13
- Git
- Docker Desktop with Docker Compose

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

