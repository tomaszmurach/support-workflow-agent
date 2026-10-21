# ADR-001: Modular monolith for the MVP

**Status:** Proposed · **Date:** 2026-10-21

## Context
A portfolio-grade AI application needs understandable boundaries and repeatable tests, but its synthetic e-commerce workload does not require independently scalable services.

## Decision
Build one FastAPI backend with API, application, domain, agent and infrastructure modules. PostgreSQL is the primary data store. Use Docker Compose locally, not microservices/Kubernetes.

## Why / trade-offs
Simpler deployment, debugging and transactions; less operational realism for distributed services. We already have a separate cloud/DevOps portfolio project, so additional Kubernetes here offers less incremental career value than robust LLM integration.

## Revisit when
An independently scaled async worker or genuinely separate service boundary is required.
