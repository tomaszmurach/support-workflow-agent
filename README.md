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

No application code or setup commands are available yet. This repository skeleton records the decisions to review before M1 (environment setup and implementation). The data used for the demo will be synthetic. Do not commit API keys, real customer information or secrets.
