# AI Agent Guidelines for ValoDiscordHub

This repository contains a monorepo for the ValoDiscordHub application, consisting of a FastAPI backend (`api/`), Discord bot (`bot/`), and React frontend (`frontend/`).

## Project Structure

- `api/`: FastAPI backend service
- `bot/`: Discord bot service (discord.py)
- `frontend/`: React frontend (Vite + TypeScript)
- `db/`: Database related scripts/configs
- `docker-compose.yml`: Local development orchestration

## 1. Build, Lint, and Test

### Dependencies
- **API**: `pip install -r api/requirements.txt`
- **Bot**: `pip install -r bot/requirements.txt`
- **Frontend**: `cd frontend && bun install` (or `npm install`/`pnpm install`)

### Running Services (Local)
- **API**: `cd api && uvicorn main:app --reload`
- **Bot**: `cd bot && python bot.py`
- **Frontend**: `cd frontend && bun dev` (or `npm run dev`/`pnpm dev`)
- **Docker**: `docker-compose up --build`

### Linting and Formatting

**Backend (Python):**
- **Formatter**: `black api/ bot/`
- **Linter**: `ruff check api/ bot/` or `flake8 api/ bot/`
- **Type Checker**: `mypy api/ bot/`

**Frontend (TypeScript):**
- **Linter**: `cd frontend && bun lint` (or `npm run lint`/`pnpm lint`)
- **Type Checker**: `cd frontend && tsc --noEmit`

**Commands:**
```bash
# Format Python code
black api/ bot/

# Lint Python code
ruff check api/ bot/

# Type check Python
mypy api/ bot/

# Lint TypeScript
cd frontend && bun lint

# Type check TypeScript
cd frontend && tsc --noEmit
```

### Testing

**Current Status**: No tests currently exist.
**Guideline**: New features MUST include unit tests.

- **Backend Framework**: `pytest`
- **Frontend Framework**: No testing framework currently configured

**Commands:**
```bash
# Run all tests (if they exist)
pytest

# Run a single test file
pytest api/tests/test_endpoints.py

# Run a specific test function
pytest api/tests/test_endpoints.py::test_health_check -v

# Run tests with coverage (if coverage configured)
pytest --cov=api --cov=bot
```

## 2. Code Style Guidelines

### General
- **Python Version**: 3.10+
- **TypeScript Version**: 5.x
- **Async Programming**: `async`/`await` is mandatory for I/O bound operations (DB, Network)
- **Docstrings**: Google style docstrings for all functions and classes
- **Frontend**: Follow React + TypeScript best practices (hooks, composition)

### Imports

**Python (sorted and organized):**
1. Standard Library (`import os`, `import asyncio`)
2. Third-party Libraries (`from fastapi import ...`, `import discord`, `import pytest`)
3. Local Application Imports (`from config import settings`, `from db import ...`)

Use absolute imports for local modules when possible to avoid circular dependency issues.

**TypeScript (Vite default):**
```typescript
// Prefer: import { something } from './utils'
// Avoid: import something from './utils' when destructuring
```

### Formatting

**Python:**
- **Line Length**: 88 characters (Black default)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes `"` for strings
- **Formatting Tool**: `black`

**TypeScript:**
- **Indentation**: 2 spaces (default in Vite + TypeScript)
- **Quotes**: Prefer single quotes for strings
- **Formatting Tool**: ESLint with recommended TypeScript rules
- **Line Length**: 80-100 characters

### Type Hinting

**Python (strong typing required):**
- Use `typing` module or standard collection types
- Use `Pydantic` models for data validation and schemas
- Return types must be explicit
- Use `|` type unions (Python 3.10+)

**TypeScript (strict mode enabled):**
```typescript
// Always annotate function parameters and return types
async function getUser(userId: number): Promise<User | null> {
    ...
}
```

### Naming Conventions

**Python:**
- **Variables/Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private Members**: Prefix with `_`

**TypeScript:**
- **Variables/Functions**: `camelCase`
- **Components**: `PascalCase`
- **Constants**: `UPPER_CASE` or `SCREAMING_SNAKE_CASE`
- **Types/Interfaces**: `PascalCase`
- **Hooks**: `camelCase` prefixed with `use`

### Error Handling

**Python:**
- Use custom exceptions for domain-specific errors
- Handle exceptions specifically; avoid bare `except:` clauses
- Use `try/except` blocks around external service calls
- Use `logging` module instead of `print`

**TypeScript:**
- Use `try/catch` for async operations
- Define custom error types when appropriate
- Use `console.error` for errors, `console.warn` for warnings
- Implement proper error boundary components in React

### Configuration

**Python:**
- Use `pydantic-settings` (see `api/config.py`)
- **NEVER** hardcode secrets or credentials
- Access configuration via the `settings` object

**TypeScript:**
- Use environment variables (prefixed with `VITE_` for client-side)
- Keep sensitive data out of client-side code

### Database (MongoDB)

**Python:**
- Use `motor` for asynchronous MongoDB operations
- Define data models using `Pydantic` in `models/` directory
- Ensure indexes are created at startup (see `api/db.py`)

**Frontend:**
- Fetch data from API endpoints
- Consider using SWR or React Query for caching
- Handle optimistic updates for better UX

### Discord Bot

**Python:**
- Use `discord.ext.commands` and `app_commands` (Slash Commands)
- Cogs: Group related commands into Cogs in `bot/cogs/`
- Interaction Responses: Always defer or respond to interactions to prevent timeouts
- Use `logger` for all bot operations

## 3. Development Workflow

1. **Understand**: Read related files before modifying
2. **Plan**: Outline changes
3. **Implement**: Write clean, typed, and documented code
4. **Verify**: Run linting and (if applicable) tests

## 4. Deployment

- Ensure changes to `api/` or `bot/` are reflected in `Dockerfile` if dependencies change
- Build frontend before deploying: `cd frontend && bun build` (or `npm run build`/`pnpm build`)
- Validate environment variables are set correctly
