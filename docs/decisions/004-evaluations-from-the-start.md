# ADR-004: Treat evaluation and observability as product requirements

**Status:** Proposed · **Date:** 2026-10-21

## Context
A plausible-sounding response does not prove correct tool selection, factual grounding, or safe execution.

## Decision
Start with deterministic contract/safety tests and a versioned set of synthetic cases. Run live-model evaluations deliberately with recorded model/prompt versions, tool selection, grounding, latency, tokens and estimated cost. No routine CI dependency on paid API calls.

## Why / trade-offs
Higher initial fixture/test investment, but quality becomes explainable and regressions measurable. This differentiates an engineered system from a chatbot demo.

## Revisit when
Expanding to model-based grading or comparing multiple providers.
