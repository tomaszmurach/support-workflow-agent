# Initial backlog — v0.1

**Status:** Planning. Estimates and assignments to Codex/Antigravity will be made when work starts.

| Issue | Milestone | Task | Acceptance signal | Owner suggestion |
|---|---|---|---|---|
| M0-01 | M0 | PRD draft | Use cases and exclusions documented | Human + technical lead |
| M0-02 | M0 | High-level architecture | Component boundaries documented | Human + technical lead |
| M0-03 | M0 | Domain and tool contracts | Entities, tool authorization and states documented | Human + technical lead |
| M0-04 | M0 | API contracts, ADRs and DoD | Draft docs reviewed | Human + technical lead |
| M1-01 | M1 | Repository bootstrap + developer environment | Project installs/tests locally | Human first, Codex assists |
| M1-02 | M1 | Postgres + migrations + synthetic fixtures | Repeatable seeded DB | Codex on isolated branch |
| M1-03 | M1 | GitHub Actions + quality gates + AGENTS.md | CI green, rules agreed | Human + Codex |
| M2-01 | M2 | Ticket read API and order service | Deterministic integration test passes | Human first |
| M2-02 | M2 | Manual provider tool-calling loop | One real order tool call end-to-end | Human first |
| M2-03 | M2 | AgentRun persistence and typed response | Readable run history; no silent schema errors | Codex assists after walkthrough |
| M3-01 | M3 | Knowledge ingestion/retrieval | Grounded retrieval and source IDs | Human + Codex |
| M3-02 | M3 | Proposals, approvals and audit | Atomic, concurrent-safe action test | Human + Codex review |
| M3-03 | M3 | LangGraph adoption decision | ADR updated using actual implementation data | Human |
| M4-01 | M4 | Evaluation dataset + harness | Reproducible baseline report | Human + Codex |
| M4-02 | M4 | Reliability and tracing | Usage/latency and failure handling visible | Human + Codex |
| M5-01 | M5 | Thin operator UI | Demonstrate proposal/review/approval | Antigravity on isolated branch |
| M5-02 | M5 | Documentation and portfolio release | README, screenshots, demo, technical defense notes | Human + both agent reviews |

**Working style:** manual-first on unfamiliar LLM/orchestration and approval semantics; delegate narrow, testable tickets later. Separate branches/worktrees and human PR review.
