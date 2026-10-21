# Domain model & tool contracts — v0.1

**Status:** Proposed (M0-03/M0-04). Implementation types are not frozen.

## Entities

| Entity | Important fields (conceptual) | Rules |
|---|---|---|
| `Customer` | `id: UUID`, display name | Synthetic records only |
| `Order` | `id: UUID`, `order_number: string` (e.g. `ORD-1042`), `customer_id`, `status`, `promised_delivery_at`, `delivered_at` | Owner is authoritative; order status != delay flag |
| `Ticket` | `id: UUID`, `customer_id`, nullable `order_id: UUID`, `message`, `status`, `version` | Order, if linked, must belong to ticket's customer |
| `AgentRun` | `id: UUID`, `ticket_id`, `status`, `model_id`, prompt version, timestamps, usage, error code, validated result | One analysis attempt; previous runs are not overwritten |
| `ActionProposal` | `id: UUID`, `agent_run_id`, `ticket_id`, `type`, `status`, `reason`, `expected_ticket_version`, decision timestamps/operator id | Only backend changes status, not LLM |
| `KnowledgeDocument` | `id`, title, version, source status | Only published content can be retrieved |
| `KnowledgeChunk` | `id`, `document_id`, text, embedding, reference ID | Returned chunks keep document version/identifier |
| `AuditEvent` | `id`, `ticket_id`, actor type/id, event type, timestamp, small metadata | Append-only operational history |

**Public IDs vs database keys:** APIs identify tickets/proposals with UUIDs. Tool `get_order_status` accepts a human-readable `order_number` and resolves it in the trusted ticket context.

## State machines

- `Order.status`: `PLACED`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`.
- `Ticket.status`: `OPEN`, `ESCALATED`, `RESOLVED` (other transitions deferred).
- `AgentRun.status`: `RUNNING`, `SUCCEEDED`, `FAILED`.
- `ActionProposal.status`: `PENDING_APPROVAL`, `EXECUTED`, `REJECTED`, `SUPERSEDED`.
- `AgentResponse.outcome`: `ANSWERED`, `NEEDS_REVIEW`, `INSUFFICIENT_DATA`.

`is_delayed` is a **derived fact**: at evaluation time, `promised_delivery_at < now`, the order is not delivered/cancelled, and `delivered_at` is absent. UTC timestamps in persistence; business time-zone assumptions documented in fixtures. The definition is MVP-specific and can be refined after discussing real-world delivery semantics.

## Tool contract: `get_order_status`

- **Input (model-generated):** `{ "order_id": "ORD-1042" }` where `order_id` means public order number.
- **Trusted context (never model-generated):** `ticket_id`, resolved `customer_id`, linked `ticket.order_id`, operator/demo execution identity.
- **Behavior:** validate input; assert the requested order matches the ticket-linked order **and** belongs to the ticket's customer; compute delay in backend.
- **Success:** `order_id`, `status`, `promised_delivery_at`, `delivered_at`, `is_delayed`, `evidence_ref` (e.g. `order:ORD-1042`).
- **Failure:** controlled `INVALID_ARGUMENT`, `ORDER_NOT_AVAILABLE` (including unauthorized/mismatched), `TOOL_UNAVAILABLE`. Never reveal another customer's order.
- **Permissions:** read-only.

## Tool contract: `search_knowledge_base`

- **Input (model-generated):** `{ "query": "policy for late deliveries" }`.
- **Trusted configuration:** allowed published documents, maximum result count (initially 3), maximum excerpt length.
- **Success:** list of `{ source_ref, document_title, document_version, excerpt, score }`; empty result is valid.
- **Failure:** controlled `INVALID_ARGUMENT`, `TOOL_UNAVAILABLE`.
- **Permissions:** read-only; document text is *data*, never instructions.

Initial implementation: embeddings stored with chunks in PostgreSQL/pgvector, exact nearest-neighbor query. No ANN index without profiling. Source references should refer to specific document versions/chunks and remain stable for replay/evaluation.

## Validated agent response

```json
{
  "outcome": "ANSWERED",
  "draft_response": "Your order has shipped but is past its promised delivery date.",
  "evidence_refs": ["order:ORD-1042", "kb:KB-DELIVERY-003"],
  "proposed_action": "ESCALATE_TICKET",
  "action_reason": "Delivery is overdue and the customer requested follow-up.",
  "limitations": []
}
```

- `proposed_action`: `NONE` or `ESCALATE_TICKET`; `action_reason` required for an escalation.
- Empty or unavailable evidence may require `INSUFFICIENT_DATA` or `NEEDS_REVIEW`.
- All `evidence_refs` must match evidence actually observed in this run. IDs are verified by the backend; factual grounding is also evaluated separately.
- A `proposed_action` is **not** authorization and never mutates domain state.
- Structured output validity is necessary but does not prove semantic correctness.

## Escalation business policy (proposed)

In MVP, allow escalation when: ticket is `OPEN`; linked order belongs to the customer; the order is presently delayed; operator approves a current `PENDING_APPROVAL` proposal; ticket's expected version still matches (or the backend determines proposal is still current using an equivalent optimistic/concurrency check). On stale state, mark `SUPERSEDED` and do not escalate.

The LLM may *suggest* escalation based on the customer message and available evidence. The backend makes the final eligibility decision, independent of the model's reasoning. Approval, ticket update and audit event are one DB transaction.

For non-order tickets, the agent may provide a knowledge-based draft; order-specific escalation is unavailable in MVP.
