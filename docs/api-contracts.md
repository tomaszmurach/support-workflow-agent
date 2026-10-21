# REST API contracts — v0.1

**Status:** Proposed. API-first discussion document, **not** an implemented OpenAPI schema.  
Base path: `/api/v1` except health endpoint. JSON request/response bodies unless stated otherwise. IDs for ticket, analysis and proposal resources are UUIDs; order numbers such as `ORD-1042` are display identifiers.

## Endpoints

| Method | Path | Purpose | Success |
|---|---|---|---|
| `GET` | `/health` | Liveness (no DB/LLM check) | `200` |
| `GET` | `/api/v1/tickets?status=OPEN&limit=20` | List tickets | `200` |
| `POST` | `/api/v1/tickets` | Create synthetic ticket | `201` |
| `GET` | `/api/v1/tickets/{ticket_id}` | Ticket detail | `200` |
| `POST` | `/api/v1/tickets/{ticket_id}/analyses` | Synchronous bounded agent analysis; persists run | `201` |
| `GET` | `/api/v1/tickets/{ticket_id}/analyses/{run_id}` | Get historical analysis/result | `200` |
| `GET` | `/api/v1/tickets/{ticket_id}/action-proposals` | List pending/completed proposals for UI | `200` |
| `POST` | `/api/v1/action-proposals/{proposal_id}/approve` | Validate and execute escalation atomically | `200` |
| `POST` | `/api/v1/action-proposals/{proposal_id}/reject` | Reject proposal atomically | `200` |
| `GET` | `/api/v1/tickets/{ticket_id}/audit-events` | Audit history | `200` |

## Representative request/response bodies

### Create a ticket

`POST /api/v1/tickets`

```json
{
  "customer_id": "11111111-1111-4111-8111-111111111111",
  "order_number": "ORD-1042",
  "message": "My delivery is late. Please escalate if needed."
}
```

Returns `201` with ticket `id`, `customer_id`, linked `order_number`, `status: OPEN`, `message`, `version: 1`, `created_at`.
Validate the linked order/customer relationship. For knowledge-only queries, `order_number` can be `null`.

### Analyze existing ticket

`POST /api/v1/tickets/{ticket_id}/analyses` with `{}` body (agent uses authoritative ticket content, not an arbitrary client-supplied system prompt).

Returns `201`:

```json
{
  "run_id": "22222222-2222-4222-8222-222222222222",
  "ticket_id": "33333333-3333-4333-8333-333333333333",
  "status": "SUCCEEDED",
  "result": {
    "outcome": "ANSWERED",
    "draft_response": "Your order has shipped but delivery is late.",
    "evidence_refs": ["order:ORD-1042", "kb:KB-DELIVERY-003"],
    "proposed_action": "ESCALATE_TICKET",
    "action_reason": "Late order, customer requested follow-up.",
    "limitations": []
  },
  "proposal_id": "44444444-4444-4444-8444-444444444444"
}
```

Return a `proposal_id` only when a **server-validated** proposal is created. Store tool-call metadata in the run record and audit trail; detail endpoint can expose sanitized information for UI.

**Execution model:** M2 uses one bounded HTTP request (not a background worker). Avoid multiple provider calls beyond configured limits. Persist `FAILED` runs where possible; error responses do not implicitly execute an approval. If observed latency makes this approach unsuitable, write a new ADR for async jobs.

### Approve a proposal

`POST /api/v1/action-proposals/{proposal_id}/approve`, body `{}`.

Returns `200`, e.g.:

```json
{
  "proposal_id": "44444444-4444-4444-8444-444444444444",
  "status": "EXECUTED",
  "ticket_status": "ESCALATED",
  "executed_at": "2026-10-21T12:00:00Z"
}
```

**Concurrency/idempotency contract:** approve pending eligible proposal once in a DB transaction. A repeated `approve` of an already executed proposal returns its existing executed result (`200`) without a second effect. `reject` on `EXECUTED` returns `409`; `approve` on `REJECTED`/`SUPERSEDED` returns `409`. A stale pending proposal becomes `SUPERSEDED`, and the request returns `409`.

`POST .../reject` similarly returns `200` for a successful or repeated rejection; conflicting transitions return `409`.

## Error envelope

```json
{
  "error": {
    "code": "PROPOSAL_STALE",
    "message": "The proposal is no longer valid for the current ticket state.",
    "request_id": "req_demo_001"
  }
}
```

| Status | When |
|---|---|
| `400` | Business input missing/inconsistent beyond schema-level validation |
| `404` | Ticket/proposal not found, or resource not visible in execution scope |
| `409` | Proposal transition conflicts with stored/current state |
| `422` | Invalid JSON shape, field types or data validation |
| `502` | Provider returned unusable data or failed upstream |
| `503` | Provider unavailable or rate-limited after bounded retry policy |
| `504` | Agent deadline exceeded |

Only stable public error codes belong in clients. Do not return provider secrets or full model traces in error bodies.

## MVP identity and authorization caveat

All actions run as a **server-configured demo operator** in a local environment; clients cannot supply an arbitrary `operator_id` and obtain new privileges. This is *not* a secure public authentication solution. Before public deployment, add real authentication and operator-level permissions. Keep backend order-scoping checks even in the demo.

## Deferred API design

Pagination cursor strategy, request-level idempotency keys for analysis creation, model streaming, async jobs/polling, externally authenticated customers and public SaaS role management. Revisit based on demonstrated requirements.
