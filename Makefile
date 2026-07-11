.PHONY: dev test lint migrate seed e2e mission-test compose-up compose-down backup restore-drill security-test

PYTHON ?= .venv/bin/python

dev:
	$(PYTHON) -m uvicorn backend.main:app --host 0.0.0.0 --port $${PORT:-8000} --reload

test:
	$(PYTHON) -m pytest backend/tests -m "not slow and not integration"

lint:
	$(PYTHON) -m py_compile backend/main.py backend/routers/mission_bridge.py backend/core/migrations.py

migrate:
	$(PYTHON) -m backend.core.migrations

seed:
	$(PYTHON) scripts/seed_mission_bridge.py

e2e:
	$(PYTHON) -m pytest backend/tests/test_mission_bridge_contract.py backend/tests/test_mission_bridge_e2e_acceptance.py

mission-test: lint e2e

compose-up:
	docker compose -f docker-compose.mission-bridge.yml up -d --build

compose-down:
	docker compose -f docker-compose.mission-bridge.yml down

backup:
	./scripts/mission_bridge_backup.sh

restore-drill:
	./scripts/mission_bridge_restore_drill.sh "$${BACKUP_FILE:?BACKUP_FILE is required}"

security-test:
	$(PYTHON) -m pytest backend/tests/test_mission_bridge_security_release.py -q
