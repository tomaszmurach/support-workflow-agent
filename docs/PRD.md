# AI Support Workflow Agent
**Product Requirements Document — v0.1**

**Status:** Draft  
**Project type:** Portfolio / Applied AI Engineering  
**Domain:** E-commerce Customer Support

## 1. Problem

Pracownicy obsługi klienta poświęcają czas na ręczne wyszukiwanie informacji o zamówieniach, sprawdzanie regulaminów oraz przygotowywanie powtarzalnych odpowiedzi.

Klasyczny chatbot nie wystarcza, ponieważ odpowiedź często wymaga dostępu do aktualnych danych biznesowych i wykonania dodatkowych czynności.

## 2. Cel produktu

Zbudowanie systemu wykorzystującego LLM do analizy zgłoszeń, pobierania informacji z różnych źródeł, przygotowywania odpowiedzi oraz proponowania działań wymagających zatwierdzenia przez operatora.

System powinien działać w sposób kontrolowany, testowalny i audytowalny.

## 3. Użytkownicy

**Support Operator:** przegląda zgłoszenia, uruchamia analizę AI, weryfikuje odpowiedzi i zatwierdza proponowane działania.

**Customer:** osoba, której zgłoszenie i zamówienia znajdują się w systemie. W MVP nie potrzebuje osobnego panelu.

## 4. User Stories

**US-01 — Order Inquiry**

As a support operator, I want the AI agent to check an order's status so that I can provide accurate information without manually searching the database.

**US-02 — Knowledge Retrieval**

As a support operator, I want the agent to consult store policies so that its responses are grounded in documented business rules.

**US-03 — Escalation Approval**

As a support operator, I want to review and approve the agent's proposed escalation so that the system cannot autonomously perform sensitive actions.

**US-04 — Auditing**

As a support operator, I want to review the agent's tool usage and decisions so that I can understand how a response or action was produced.

## 5. MVP Functional Requirements

- Create and retrieve support tickets.
- Analyze a ticket using a real LLM API.
- Retrieve order information through a controlled backend tool.
- Retrieve relevant information from a knowledge base.
- Generate a structured, validated draft response.
- Propose escalation when appropriate.
- Require explicit approval before executing escalation.
- Record tool calls, approval decisions and business actions.
- Handle API errors, missing information and invalid tool arguments.

## 6. Non-Functional Requirements

- Python backend with clearly separated responsibilities.
- Deterministic tests without mandatory external API calls.
- Reproducible local setup using Docker.
- Secure API key handling.
- LLM request timeouts and execution limits.
- Structured logging and basic usage/cost tracking.
- Evaluation dataset with reproducible test cases.

## 7. Out of Scope

- Real e-commerce integrations.
- Payment and refund processing.
- Autonomous execution of sensitive business operations.
- Multi-agent orchestration.
- Complex customer authentication and production-grade RBAC.
- Advanced frontend and mobile application.

## 8. Success Criteria

The MVP is successful when a support operator can process a synthetic customer ticket end-to-end, receive a factually grounded draft response, inspect the agent's tool usage, and approve or reject a proposed escalation.

Every sensitive action must require explicit approval, and the core workflow must be covered by automated tests and measurable LLM evaluations.