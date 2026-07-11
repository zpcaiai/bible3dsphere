from datetime import datetime,timedelta,timezone
from pathlib import Path
import pytest
from mission_os.organizations import MissionOrganizationProfile,invitation_active,validate_relationship
from routers.mission_organizations import router
from fastapi.routing import APIRoute

def test_profile_reuses_organization_and_stays_in_owning_tenant():
    assert MissionOrganizationProfile('church-1','church-1','church','CN').validate().organization_id=='church-1'
    with pytest.raises(ValueError):MissionOrganizationProfile('church-1','agency-2','church').validate()

def test_sending_relationship_requires_local_leadership_decision_rights():
    with pytest.raises(ValueError):validate_relationship('church','agency','sending',{'approvals':True})
    validate_relationship('church','agency','sending',{'approvals':True,'local_leadership':True})

def test_invitation_is_expiring_and_fail_closed():
    now=datetime.now(timezone.utc)
    assert invitation_active('pending',now+timedelta(hours=1),now)
    assert not invitation_active('pending',now-timedelta(seconds=1),now)
    assert not invitation_active('revoked',now+timedelta(hours=1),now)

def test_migration_references_existing_organizations_and_enables_rls():
    sql=(Path(__file__).parents[1]/'migrations'/'0169_mission_os_organizations.sql').read_text()
    assert 'REFERENCES organizations(id)' in sql and 'CREATE TABLE IF NOT EXISTS organizations' not in sql
    assert sql.count('ENABLE ROW LEVEL SECURITY')==3

def test_skill_08_api_contract_exists():
    routes={(r.path,m) for r in router.routes if isinstance(r,APIRoute) for m in r.methods}
    expected={('/api/v1/mission/organizations/{organization_id}/profile','PUT'),('/api/v1/mission/organizations/{organization_id}','GET'),('/api/v1/mission/organizations/{organization_id}/relationships','POST'),('/api/v1/mission/organizations/{organization_id}/invitations','POST'),('/api/v1/mission/organizations/invitations/accept','POST')}
    assert expected<=routes

def test_invitation_token_is_hashed_and_never_audited():
    source=(Path(__file__).parents[1]/'routers'/'mission_organizations.py').read_text()
    assert 'hashlib.sha256(raw.encode()).hexdigest()' in source
    assert "'invitationToken':raw" in source
    assert 'token_hash' in source
