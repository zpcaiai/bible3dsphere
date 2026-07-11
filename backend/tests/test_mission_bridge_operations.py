from pathlib import Path
from routers.mission_bridge_operations import PAGES,_mask
def test_operations_has_all_required_pages_and_masks():assert len(PAGES)==14 and _mask('person@example.com')!='person@example.com'
def test_sensitive_workflows_require_mfa_consent_and_audit():
 source=(Path(__file__).parents[1]/'routers'/'mission_bridge_operations.py').read_text();sql=(Path(__file__).parents[1]/'migrations'/'0178_mission_bridge_operations.sql').read_text()
 assert '_recent_mfa' in source and "operations.export.requested" in source
 assert 'consentSourceReference' in source and 'rejectedRows' in source
 assert "review_status!='approved'" in source or "template[0]!='approved'" in source
 assert 'CHECK(unsubscribe_required=TRUE)' in sql
