# ============================================================
# SFDS v3 — Makefile
# ============================================================

.PHONY: help up down build seed test lint format reset

help:
	@echo ""
	@echo "SFDS v3 — Human Formation Intelligence System"
	@echo "=============================================="
	@echo "make up           Start full stack"
	@echo "make down         Stop all services"
	@echo "make build        Rebuild all containers"
	@echo "make seed         Seed all databases"
	@echo "make seed-graph   Seed Neo4j patterns only"
	@echo "make seed-vec     Seed pgvector principles only"
	@echo "make migrate      Run DB migrations"
	@echo "make test         Run full test suite"
	@echo "make test-unit    Run unit tests only"
	@echo "make test-integ   Run integration tests"
	@echo "make lint         Lint all Python + TS"
	@echo "make format       Auto-format all code"
	@echo "make logs         Tail API logs"
	@echo "make reset        Nuclear reset (destroys volumes)"
	@echo ""

up:
	docker compose up -d
	@echo "SFDS v3 stack started. API: http://localhost:8000  Web: http://localhost:3000"

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f api

# ── Database operations ──────────────────────────────────────

migrate:
	@echo "Running Postgres migrations..."
	docker compose exec postgres psql -U sfds -d sfds -f /docker-entrypoint-initdb.d/001_core.sql
	@echo "Running Timescale migrations..."
	docker compose exec timescale psql -U sfds -d sfds_timescale -f /docker-entrypoint-initdb.d/001_timescale.sql

seed: seed-graph seed-vec seed-principles
	@echo "All databases seeded."

seed-graph:
	docker compose exec api python scripts/seed_graph_patterns.py

seed-vec:
	docker compose exec api python scripts/rebuild_embeddings.py

seed-principles:
	docker compose exec api python scripts/seed_principles.py

# ── Testing ──────────────────────────────────────────────────

test:
	docker compose exec api pytest tests/ -v --tb=short

test-unit:
	docker compose exec api pytest tests/unit/ -v

test-integ:
	docker compose exec api pytest tests/integration/ -v

test-graph:
	docker compose exec api pytest tests/graph_tests/ -v

# ── Code quality ─────────────────────────────────────────────

lint:
	cd apps/api && ruff check .
	cd apps/web && npx eslint .

format:
	cd apps/api && ruff format . && isort .
	cd apps/web && npx prettier --write .

# ── Danger zone ──────────────────────────────────────────────

reset:
	@echo "⚠️  This will destroy all data volumes. Ctrl+C to cancel."
	@sleep 3
	docker compose down -v
	@echo "Volumes destroyed. Run 'make up && make migrate && make seed' to reinitialize."

# ── Dev shortcuts ─────────────────────────────────────────────

dev-api:
	cd apps/api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-web:
	cd apps/web && npm run dev
