#!/usr/bin/env bash
set -euo pipefail
: "${RESTORE_DATABASE_URL:?RESTORE_DATABASE_URL is required}"
: "${1:?backup dump path is required}"
pg_restore --clean --if-exists --no-owner --no-acl --dbname "$RESTORE_DATABASE_URL" "$1"
psql "$RESTORE_DATABASE_URL" -v ON_ERROR_STOP=1 -c "SELECT COUNT(*) FROM mission_bridge_program_definitions;"
