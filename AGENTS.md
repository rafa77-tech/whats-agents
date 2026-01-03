# Repository Guidelines

## Source of Truth & Current State

- `CLAUDE.md` is the source of truth for project status, completed sprints, and operating rules.
- Current sprint status in `CLAUDE.md` should guide scope and priorities before starting work.

## Project Structure & Module Organization

- `app/` holds the FastAPI application (routes, services, tools, pipeline, prompts, workers, core config).
- `tests/` contains pytest suites; keep unit and integration tests here.
- `docs/` hosts architecture, setup, operations, integrations, and templates.
- `dashboard/` contains the web dashboard (Next.js/TypeScript).
- `migrations/`, `supabase/`, and `docker-compose.yml` support database and infra.

## Build, Test, and Development Commands

- `uv sync` installs Python dependencies using uv.
- `uv run pytest` runs the full test suite.
- `./run.sh` starts the FastAPI server via Uvicorn on port 8000.
- `docker compose up -d` starts the local services (Evolution API, Chatwoot, n8n, Postgres, Redis, PgAdmin).
- `docker compose logs -f <service>` tails logs for a specific container.

## Coding Style & Naming Conventions

- Python uses 4-space indentation and explicit type hints for all functions.
- I/O functions must be `async`; keep sync logic for pure computation only.
- Follow naming prefixes from `app/CONVENTIONS.md` (e.g., `buscar_`, `listar_`, `criar_`, `atualizar_`).
- Keep constants in `app/core/config.py` and import settings from there.
- Format with Black and lint with Ruff; line length is 100 and target is Python 3.13.
- Imports are ordered: standard library, third-party, local.

## Testing Guidelines

- Frameworks: `pytest` + `pytest-asyncio` (`asyncio_mode = auto`).
- Name tests as `test_*.py` and use `Test*` classes for grouped behaviors.
- Run `uv run pytest` before submitting changes; keep fixtures scoped to functions unless needed.

## Commit & Pull Request Guidelines

- Commit messages follow Conventional Commits, typically `type(scope): summary` (e.g., `feat(dashboard): add auth flow`).
- Check your branch before committing: `git branch --show-current`.
- PRs should include a short summary, testing notes, and linked issues.
- For dashboard/UI changes, add screenshots or recordings.

## Configuration & Secrets

- Copy `.env.example` to `.env` and keep secrets out of git.
- Ports and service URLs are defined in `docker-compose.yml` and README.

## Integration & Frontend Rules

- For external services, consult local docs in `docs/integracoes/` before searching online.
- For dashboard (Next.js/TypeScript), follow `docs/best-practices/nextjs-typescript-rules.md` and run:
  `npm run tsc -- --noEmit`, `npm run lint`, `npm run format`, `npm test`, `npm run build`.
