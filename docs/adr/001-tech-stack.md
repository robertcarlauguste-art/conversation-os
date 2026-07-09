# ADR-001: Technology Stack

## Status
Accepted

## Context
ConversationOS needs a stack that supports an AI-powered relationship
intelligence layer sitting on top of existing CRMs. The MVP customer
is a Realtor, but the architecture must generalize to insurance,
legal, recruiting, and financial-advisory verticals without a rewrite.
That means the stack needs: strong typing end-to-end, async I/O
(conversations and AI calls are inherently I/O-bound), a vector-capable
database for future semantic memory/search, and a component ecosystem
mature enough to move fast in Sprint 1+ without reinventing UI
primitives.

## Decision
- **Frontend:** Next.js 15, React, TypeScript, TailwindCSS, shadcn/ui,
  TanStack Query.
- **Backend:** Python 3.13, FastAPI, uv (package manager), Pydantic v2,
  SQLAlchemy 2 (async), Alembic.
- **Infrastructure:** PostgreSQL 16 with pgvector, Redis, Docker
  Compose for local orchestration, GitHub Actions for CI.
- **Auth (scaffold only, not implemented this sprint):** Clerk + JWT.

## Consequences
- Async-first backend (FastAPI + SQLAlchemy 2 async) adds a small
  amount of ceremony (async session management, async test client)
  but avoids a rewrite when AI calls and webhooks become the norm.
- pgvector at the infrastructure layer means semantic search/memory
  in later sprints doesn't require introducing a separate vector
  database — one less moving part to operate.
- uv as the Python package manager is a newer tool than pip/poetry;
  the team accepts a small learning-curve cost in exchange for
  faster, more reproducible installs.
- Locking the stack now means any deviation in a future sprint
  requires a new ADR rather than an ad-hoc substitution.
