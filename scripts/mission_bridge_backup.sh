#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL is required}"
output="${1:-mission-bridge-$(date -u +%Y%m%dT%H%M%SZ).dump}"
pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" > "$output"
pg_restore --list "$output" >/dev/null
printf '%s\n' "$output"
