#!/usr/bin/env bash
# Mission OS migration smoke: applies all migrations from an empty PostgreSQL and
# verifies Batch 1-6 tables + RLS. Uses $DATABASE_URL if set, otherwise spins up a
# throwaway Docker PostgreSQL. Also runs the DB-gated pytest suite when a DB is up.
#
#   ./scripts/mission_os/migration_smoke.sh
#   DATABASE_URL=postgresql://u:p@host:5432/db ./scripts/mission_os/migration_smoke.sh
set -euo pipefail
cd "$(dirname "$0")/../.."   # -> backend/

CONTAINER=""
cleanup() { [ -n "$CONTAINER" ] && docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup EXIT

if [ -z "${DATABASE_URL:-}" ]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "[SMOKE] no DATABASE_URL and no docker; set DATABASE_URL to a PostgreSQL and re-run." >&2
    exit 2
  fi
  echo "[SMOKE] starting throwaway PostgreSQL via docker ..."
  CONTAINER="mission_smoke_pg_$$"
  docker run -d --name "$CONTAINER" -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=missionsmoke -p 55432:5432 postgres:15 >/dev/null
  # Prefer a non-superuser app role so RLS enforcement is actually exercised.
  for i in $(seq 1 30); do
    if docker exec "$CONTAINER" pg_isready -U postgres >/dev/null 2>&1; then break; fi
    sleep 1
  done
  docker exec "$CONTAINER" psql -U postgres -d missionsmoke -c \
    "CREATE ROLE mission_app LOGIN PASSWORD 'app'; GRANT ALL ON SCHEMA public TO mission_app;" >/dev/null
  export MIGRATION_URL="postgresql://postgres:postgres@localhost:55432/missionsmoke"
  export DATABASE_URL="postgresql://mission_app:app@localhost:55432/missionsmoke"
else
  export MIGRATION_URL="$DATABASE_URL"
fi

echo "[SMOKE] applying migrations as owner, verifying as app role ..."
# Apply migrations as the privileged role (owns objects), then run the smoke
# checks as the app role so RLS is enforced behaviourally.
DATABASE_URL="$MIGRATION_URL" python3 - <<'PY'
import os; from core.migrations import run_migrations
print("[SMOKE] applied", len(run_migrations(os.environ["DATABASE_URL"])), "migrations")
PY
# Grant the app role access to the freshly created tables, then run verification.
if [ -n "$CONTAINER" ]; then
  docker exec "$CONTAINER" psql -U postgres -d missionsmoke -c \
    "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO mission_app;" >/dev/null
fi
python3 scripts/mission_os/migration_smoke.py

# Optional: run DB-gated mission tests if pytest + a DB are available.
if python3 -c "import pytest" >/dev/null 2>&1; then
  echo "[SMOKE] running mission test suite (no_db + any DB-gated) ..."
  python3 -m pytest tests/test_mission_*.py -q || true
fi
echo "[SMOKE] done."
