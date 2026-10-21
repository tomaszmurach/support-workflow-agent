
# AI Support Workflow Agent — Agent Instructions

## Project Context

This repository contains a Python-based AI Support Copilot
for e-commerce customer support operators.

The application uses FastAPI, PostgreSQL and LLM APIs to
analyze tickets, retrieve information and propose actions.

Human approval is required for business-state changes.

## Source of Truth

- `docs/PRD.md` — product scope and requirements.
- `docs/architecture.md` — architecture and boundaries.
- `docs/domain-model.md` — domain entities and tool contracts.
- `docs/api-contracts.md` — REST API contracts.
- `docs/acceptance-criteria.md` — acceptance criteria.
- `docs/decisions/` — architecture decisions.

Read the relevant documents before modifying a component.
Do not treat proposed designs as implemented functionality.

## Engineering Standards

- Python 3.13.
- FastAPI and Pydantic for API contracts.
- Use type hints for public functions.
- Prefer straightforward, testable code.
- Follow existing project conventions.
- Avoid unnecessary dependencies and abstractions.
- Do not introduce new frameworks without justification.
- Do not refactor unrelated code.

## Architecture Boundaries

- LLM-generated output is untrusted.
- Never grant an LLM direct database access.
- Validate tool arguments in the backend.
- Keep business rules outside LLM prompts.
- Model-generated actions require backend validation.
- Sensitive operations require human approval.
- Do not bypass authorization or approval checks.

## Testing

For code changes, run relevant tests and quality checks:

- `python -m pytest -v`
- `python -m ruff check .`
- `python -m ruff format --check .`

Add or update tests when modifying behavior.
Use mocks or stubs for external LLM calls in unit tests.
Never require paid API calls in the standard test suite.

## Agent Working Agreement

- Work only within the explicitly approved task scope.
- Explain assumptions and important trade-offs.
- Ask before making architectural decisions.
- Ask before adding dependencies or database migrations.
- Do not modify unrelated files.
- Do not commit, push, merge or deploy without approval.
- Do not access or expose credentials and secrets.
- Do not run destructive commands without approval.
- Report changed files and verification results.
- Clearly distinguish verified results from assumptions.

## Collaboration

Codex and Antigravity may work on the same repository.

- One implementation owner per task.
- Use separate branches or worktrees for concurrent work.
- Avoid simultaneous edits to the same files.
- Use Pull Requests for code review.
- Human approval is required before merging.
