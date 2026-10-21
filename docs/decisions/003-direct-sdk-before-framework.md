# ADR-003: Direct model SDK first; assess LangGraph after one vertical slice

**Status:** Proposed · **Date:** 2026-10-21

## Context
Tool/function calling and stateful orchestration are important entry-level GenAI engineering skills. An immediate framework dependency can obscure basic provider semantics.

## Decision
Implement one bounded tool-calling loop with the provider SDK in M2; use Pydantic for input/output contracts. Re-evaluate LangGraph during M3 for meaningful workflow state, branching, checkpointing or interrupt/resume. Do not mix multiple orchestration frameworks without a demonstrated need.

## Why / trade-offs
Manual SDK work provides deeper understanding and lower abstraction overhead; LangGraph has practical market visibility and supports durable workflow constructs, but introduces state/checkpoint complexity. The final decision must cite an actual pain point or benefit, not a CV keyword alone.

## Revisit when
The M2 loop works and M3 requirements are tangible. Record a small comparison (code complexity, observability, testability, failure semantics).
