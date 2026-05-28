# Repository Guidelines

## Project Structure & Module Organization

This repository combines Python retrieval services, data scripts, and a Vite React UI.

- `backend/` contains the FastAPI/backend domain code, SQL schemas, MVFE modules, and `backend/tests/`.
- `scripts/` contains vectorization, Qdrant indexing, emotion matching, reporting, and layout-generation utilities.
- `bible/` stores Bible CSV source data.
- `emotion-sphere-ui/` is the React/Three.js frontend. Source lives in `src/`, static assets in `public/`, and generated production output in `dist/`.
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

Run the frontend:

```bash
cd emotion-sphere-ui
npm install
npm run dev
npm run build
```

Use `npm run preview` to inspect a production build locally.

## Coding Style & Naming Conventions

Use Python 3.11-compatible code with 4-space indentation, typed function boundaries where practical, and snake_case for modules, functions, and variables. Keep scripts executable as direct CLI tools when they are already structured that way.

React components use PascalCase filenames such as `EmotionSphereScene.jsx`; hooks use `useX.js`; helpers use lower camelCase exports in concise modules like `api.js` and `utils.js`. Prefer existing state/API patterns over introducing new global abstractions.

## Testing Guidelines

Backend tests use pytest. Test files must match `test_*.py`, classes `Test*`, and functions `test_*`, as configured in `backend/tests/pytest.ini`. Mark long-running tests with `@pytest.mark.slow` and external-service tests with `@pytest.mark.integration` so they can be filtered.

There is no configured frontend test runner; for UI changes, run `npm run build` and manually verify the affected route or component.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit prefixes, especially `feat:` and `fix:`. Keep messages imperative and scoped to one behavior, for example `fix: prevent mobile page width overflow`.

Pull requests should include a short problem statement, a summary of changes, test/build results, linked issues when applicable, and screenshots or recordings for visible UI changes. Note any generated data artifacts that were intentionally refreshed.

## Security & Configuration Tips

Do not commit secrets, API keys, or local `.venv` contents. Treat generated vector indexes, cache files, and database snapshots as large artifacts: update them only when the change explicitly requires regenerated retrieval data.
