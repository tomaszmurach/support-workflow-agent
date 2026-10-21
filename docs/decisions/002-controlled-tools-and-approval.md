# ADR-002: Read-only model tools and backend-controlled approval

**Status:** Proposed · **Date:** 2026-10-21

## Context
A model can be influenced by ticket text, retrieved documents or malformed tool output. It must not directly change business records or trust an arbitrary order identifier.

## Decision
Expose only bounded read tools to the model in the MVP. Resolve customer/ticket permissions from backend-controlled context. Represent writes as `ActionProposal` records; approvals run outside the model, inside a DB transaction with current-state revalidation and audit logging.

## Why / trade-offs
More domain code and extra operator clicks, but strong separation of interpretation vs authority. Useful for discussing real AI security and failure modes in interviews.

## Revisit when
Introducing safe, explicitly scoped, reversible automation with a written risk assessment.
