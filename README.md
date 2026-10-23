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

- **Implemented:** Python 3.13 package setup, FastAPI application with a typed `GET /health` endpoint, pytest/Ruff configuration, local PostgreSQL 17 with pgvector managed by Docker Compose, and Customer/Order/Ticket ORM models. Migration `0001` has been executed successfully on the local development database. DB-02A/B/C and the accepted review fixes are complete and manually validated: PostgreSQL integration suite **40 passed, 70 deselected**; default/offline suite **70 passed, 40 skipped**. The test database had zero user tables after the run, and the development database remained at Alembic revision `0001` with all four expected tables intact.
- **Next (remaining M1 foundations):** Synthetic fixtures and GitHub Actions quality gates (M1-03; not yet implemented).
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

### Database migrations

Install the development extra (`python -m pip install -e ".[dev]"`) for Alembic
and python-dotenv. Psycopg 3 with binary support is a runtime dependency for
PostgreSQL connectivity. Migration commands run synchronously using `alembic`
from the activated Python virtual environment.

Online commands read `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`
from the repository-root `.env`. Process environment variables take precedence.
`POSTGRES_HOST` and `POSTGRES_PORT` can also be set in either location; they
default to `127.0.0.1` and `5433`. Values are passed through SQLAlchemy
`URL.create()` without URL-string interpolation. Dotenv variable interpolation
is disabled to preserve literal password characters. Never commit `.env` or
put credentials in `alembic.ini`.

Inspect revisions and render SQL without connecting or reading credentials:

```powershell
alembic heads
alembic history
alembic upgrade head --sql
alembic downgrade 0001:base --sql
```

For a fresh checkout with a newly prepared local development database, apply
the schema and inspect its revision after maintainer approval:

```powershell
alembic upgrade head
alembic current
```

The existing development database is already at `0001`; it does not need to be
reset. Downgrade deletes all three application tables and their data. Only run
it against an explicitly approved target:

```powershell
alembic downgrade base
```

For later model changes, use `alembic revision --autogenerate -m "description"`
against an approved development database and manually review the generated file.
`alembic/env.py` explicitly imports the models before assigning `Base.metadata`;
it currently verifies that exactly `customers`, `orders`, and `tickets` are registered.
Update this guard when intentionally introducing additional models.

Revision `0001` was started with Alembic's autogenerate API against an empty
in-memory SQLite database, then corrected and checked as PostgreSQL SQL.
It enables `vector` with `CREATE EXTENSION IF NOT EXISTS vector` and creates
the three application tables with their named constraints. This revision has
been applied successfully to local development PostgreSQL. When applying it
for the first time to another local database, the target must not already
contain these application tables; review any existing schema before applying.
PostgreSQL must have pgvector available and the migration role must be permitted
to create the extension. Downgrade drops `tickets`, `orders`, then `customers`,
but deliberately retains `vector`, which may predate this migration or be shared.

### PostgreSQL integration tests (DB-02C)

The PostgreSQL suite is in `tests/integration/` and marked `postgres`. Normal
`python -m pytest -v` skips it, and `python -m pytest -m "not postgres" -v`
runs only unit/offline tests. Selecting `-m postgres` alone does not enable
database access: the explicit `--run-postgres` flag is also required. Collection
does not run fixtures or connect, even when that flag is present.

**Review and obtain human approval before executing any setup or integration
commands below.** The maintainer has validated the final DB-02C review fixes:
PostgreSQL integration suite **40 passed, 70 deselected**; default/offline suite
**70 passed, 40 skipped**. The test database had zero user tables after the run,
and the development database remained at Alembic revision `0001`. The suite
remains opt-in, with the same isolation guards required for each run.

#### One-time setup after approval

Use only the local Docker development cluster. The suite deliberately accepts
only database **`support_workflow_test`**, role **`support_workflow_test`**, and
address **`127.0.0.1:5433`**. Do not point this port at production or use a tunnel.
The role must own the test database, have no role memberships, and have no
superuser, database-creation, role-creation, replication, or RLS-bypass privileges.
Do not grant it access to development tables or any other database's objects.

Open an administrator psql session in the local container (the existing Compose
example uses administrator `support_agent`):

```powershell
docker compose exec db psql -U support_agent -d postgres -v ON_ERROR_STOP=1
```

Run these SQL/psql commands interactively. `\password` prompts without placing
the password in command history. If the role or database already exists, stop
and inspect it; do not drop, reset, or reuse a populated database.

```sql
CREATE ROLE support_workflow_test LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
\password support_workflow_test
CREATE DATABASE support_workflow_test OWNER support_workflow_test;
\connect support_workflow_test
CREATE EXTENSION IF NOT EXISTS vector;
\quit
```

Preinstalling pgvector allows the test role to remain unprivileged. The migration
still executes its `CREATE EXTENSION IF NOT EXISTS vector` statement, and the
lifecycle test verifies downgrade preserves the existing extension. Installing
a previously absent extension as an administrator is not covered by this suite.

#### Configuration and execution after approval

Supply all five test-specific variables in PowerShell. There are no fallbacks
to `POSTGRES_*`, `.env`, or the development migration URL. Missing or unsafe
settings cause an error before engine creation. The test password is separate
from the development password; never commit it or print the connection URL.

CI **must not use `pytest --showlocals` or `-l`**, including through
`PYTEST_ADDOPTS`. Opted-in PostgreSQL runs reject that setting before fixtures
initialize. CI must store the test password as a masked secret and enable log
redaction for it (and any encoded form that could be emitted); never echo it or
dump the environment. No CI workflow is introduced here.

Test configuration reads individual allowlisted environment keys, without
passing or copying the full environment into fixtures. Normal SQLAlchemy URL
representations mask passwords, engine echo is disabled, and SQL parameter
logging is hidden. Sensitive setup frames are hidden from ordinary pytest
tracebacks. These measures do not erase credentials from memory: the driver
must receive the password, and third-party traceback frames, debuggers, or
custom diagnostic plugins can expose it. Do not use full-trace/local-variable
dumps with real credentials. Restrict access to CI logs and keep secret masking
enabled rather than relying on allowlisting alone.

```powershell
$env:TEST_POSTGRES_DB = 'support_workflow_test'
$env:TEST_POSTGRES_USER = 'support_workflow_test'
$env:TEST_POSTGRES_HOST = '127.0.0.1'
$env:TEST_POSTGRES_PORT = '5433'
$testPassword = Read-Host 'Test database password' -AsSecureString
$env:TEST_POSTGRES_PASSWORD = [System.Net.NetworkCredential]::new('', $testPassword).Password

python -m pytest --run-postgres -m postgres -v

Remove-Item Env:TEST_POSTGRES_PASSWORD
Remove-Variable testPassword
```

Run serially, without pytest-xdist. Unset `PGSERVICE`, `PGSERVICEFILE`,
`PGHOSTADDR`, and `PGOPTIONS` if present; the suite rejects libpq overrides
that could redirect a connection. A transaction-scoped advisory lock rejects
concurrent suite runs on this database. Do not use the database for other work.

Before migrations, fixtures query `current_database()`, `current_user`, role
privileges, memberships, and database ownership on the actual connection.
They refuse any existing user tables, views, materialized views, foreign tables,
or sequences in any user schema. No reset is attempted. The `vector` extension
must already be installed.

Alembic receives that same verified connection through `Config.attributes`;
it never reads development credentials or opens a second connection. Tests set
`configure_logger=False` so Alembic does not replace pytest's logging handlers;
normal Alembic CLI commands retain their standard logging configuration. Each test
creates its schema through `upgrade head` within a savepoint. ORM sessions use
their own savepoints; expected constraint errors roll back without leaving an
aborted transaction. Per-test cleanup rolls back DDL and rows. Session cleanup
rolls back the enclosing transaction and closes the connection, leaving the
initial empty test database and preinstalled pgvector unchanged, including on
ordinary test failures or disconnects. No database, volume, or cluster is dropped.

The lifecycle test independently starts empty, upgrades, verifies tables and
revision `0001`, downgrades, verifies application tables are absent and pgvector
remains, then upgrades again and compares normalized schema metadata from both
upgrades: columns and types, nullability, defaults, primary keys, foreign keys,
UNIQUE and CHECK constraints. Unstable catalog OIDs are excluded. All of this is
transactional and rolled back: it tests actual PostgreSQL DDL, but not persistence
across a committed migration followed by a new connection.

Coverage includes duplicate primary keys, referenced-customer deletion,
named FK/unique/CHECK constraints, required-column NULL
rejection, nullable order links, server defaults, UUIDs, timezone-aware datetimes,
all order/ticket statuses, and persisted relationship ownership. The redundant
`orders(id, customer_id)` unique constraint is checked through PostgreSQL
introspection because the primary key independently rejects duplicate IDs.

Safe validation before approval (no PostgreSQL access):

```powershell
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
alembic heads
python -m pytest --collect-only -m postgres --run-postgres -q
python -m pytest --markers
```

