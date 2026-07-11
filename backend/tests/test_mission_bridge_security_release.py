from pathlib import Path
def test_release_security_controls_are_documented_and_wired():
 root=Path(__file__).parents[2];doc=(root/'docs/mission-bridge/DEPLOYMENT_SECURITY.md').read_text();compose=(root/'docker-compose.mission-bridge.yml').read_text();requirements=(root/'backend/requirements.txt').read_text()
 for term in ('RLS bypass','IDOR','Minor-record','Prompt injection','RAG','Malicious uploads','Export permission','Sensitive-data log','Session fixation','CSRF and XSS'):assert term in doc
 assert 'internal: true' in compose and 'OTEL_EXPORTER_OTLP_ENDPOINT' in compose
 assert 'slowapi' in requirements and 'opentelemetry-sdk' in requirements
def test_backup_and_restore_scripts_fail_closed():
 root=Path(__file__).parents[2];backup=(root/'scripts/mission_bridge_backup.sh').read_text();restore=(root/'scripts/mission_bridge_restore_drill.sh').read_text()
 assert 'set -euo pipefail' in backup and 'DATABASE_URL is required' in backup
 assert 'set -euo pipefail' in restore and 'RESTORE_DATABASE_URL is required' in restore
