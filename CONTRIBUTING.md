# Contributing to ASC

Thank you for helping improve safe agentic commerce.

## Development workflow

1. Create a focused branch from main.
2. Keep AI outputs inside validated Pydantic contracts.
3. Keep commercial calculations and authorization deterministic.
4. Add or update regression tests for behavior changes.
5. Run the backend suites and frontend lint/build before opening a pull request.

## Architectural rules

- AI may interpret, propose and explain; it may not authorize a commercial decision.
- Every executable offer must pass all six Control Plane gates.
- Use SQLAlchemy, SessionLocal and Alembic for persistence.
- Never commit environment files, API keys, merchant passcodes or local databases.
- Keep buyer-facing responses free of merchant costs and private policy details.

See [AGENTS.md](AGENTS.md) and [development phases](docs/phases/README.md) for the
complete implementation context.
