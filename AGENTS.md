# Repository Guidelines

## Project Structure & Module Organization

This repository is the **pure Python API backend** for 属灵星球 (holiness.uk). The React/Vite frontend lives in the separate **bible3dsphere-frontend** repo.

- `backend/` contains the FastAPI/backend domain code, SQL schemas, MVFE modules, and `backend/tests/`.
- `scripts/` contains vectorization, Qdrant indexing, emotion matching, reporting, and layout-generation utilities.
- `bible/` stores Bible CSV source data.
- Frontend source has moved to the **bible3dsphere-frontend** repository (not present in this repo).
- Root JSON/NPY/PKL/DB files are generated data artifacts used by search and sphere layout flows.

## Build, Test, and Development Commands

Create Python dependencies from the repository root:

```bash
python3.11 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pip install -r backend/requirements.txt
```

Run backend tests:

```bash
cd backend && ../.venv/bin/python -m pytest
```

Run the emotion API locally:

```bash
./.venv/bin/python scripts/emotion_api_server.py
```

Run the frontend (separate repo):

```bash
# Clone bible3dsphere-frontend and follow its README.
# Point VITE_API_BASE at http://localhost:7860 for local backend dev.
```

## Coding Style & Naming Conventions

Use Python 3.11-compatible code with 4-space indentation, typed function boundaries where practical, and snake_case for modules, functions, and variables. Keep scripts executable as direct CLI tools when they are already structured that way.

React components use PascalCase filenames such as `EmotionSphereScene.jsx`; hooks use `useX.js`; helpers use lower camelCase exports in concise modules like `api.js` and `utils.js`. Prefer existing state/API patterns over introducing new global abstractions.

## Testing Guidelines

Backend tests use pytest. Test files must match `test_*.py`, classes `Test*`, and functions `test_*`, as configured in `backend/tests/pytest.ini`. Mark long-running tests with `@pytest.mark.slow` and external-service tests with `@pytest.mark.integration` so they can be filtered.

Frontend tests live in the bible3dsphere-frontend repo. Backend tests use pytest as described above.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit prefixes, especially `feat:` and `fix:`. Keep messages imperative and scoped to one behavior, for example `fix: prevent mobile page width overflow`.

Pull requests should include a short problem statement, a summary of changes, test/build results, linked issues when applicable, and screenshots or recordings for visible UI changes. Note any generated data artifacts that were intentionally refreshed.

## Security & Configuration Tips

Do not commit secrets, API keys, or local `.venv` contents. Treat generated vector indexes, cache files, and database snapshots as large artifacts: update them only when the change explicitly requires regenerated retrieval data.
