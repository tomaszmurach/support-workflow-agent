# ADR-005: Bounded synchronous analysis for the first MVP slice

**Status:** Proposed · **Date:** 2026-10-21

## Context
An analysis may involve several model/tool calls. A durable queue/worker would add significant scope before we have measured run time.

## Decision
The M2 `POST /tickets/{ticket_id}/analyses` request runs synchronously with strict deadline/tool-call/retry caps, persists `AgentRun`, and returns a result or controlled error. Human approval is a separate later HTTP transaction; the analysis request does not wait for it.

## Why / trade-offs
Easy to debug and demonstrate; risks client timeouts and duplicate analysis creation on retry. Document this limitation, keep side effects limited to run/proposal records, and reassess after measuring latency. Approval operations **are** concurrency-safe and idempotent independently.

## Revisit when
Run durations or failure rates justify an async job queue + worker with durable execution.
