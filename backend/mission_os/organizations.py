"""Mission organization invariants without duplicating the Organization aggregate."""
from dataclasses import dataclass
from datetime import datetime,timezone

ORGANIZATION_KINDS=frozenset({'church','mission_agency','receiving_church','team','training_provider','care_provider','professional_partner','funding_partner'})
RELATIONSHIP_TYPES=frozenset({'sending','receiving','partner','training','member_care','professional_referral','funding'})

@dataclass(frozen=True)
class MissionOrganizationProfile:
    organization_id:str;tenant_id:str;organization_kind:str;country_code:str|None=None
    def validate(self):
        if self.organization_kind not in ORGANIZATION_KINDS:raise ValueError('invalid mission organization kind')
        if self.country_code and (len(self.country_code)!=2 or not self.country_code.isalpha()):raise ValueError('country code must be ISO alpha-2')
        if self.organization_id!=self.tenant_id:raise ValueError('organization profile must remain in its owning tenant')
        return self

def validate_relationship(source_id:str,target_id:str,relationship_type:str,decision_rights:dict)->None:
    if source_id==target_id:raise ValueError('organization cannot partner with itself')
    if relationship_type not in RELATIONSHIP_TYPES:raise ValueError('invalid relationship type')
    if relationship_type in {'sending','receiving'} and not {'approvals','local_leadership'}<=set(decision_rights):raise ValueError('sending relationships require explicit approvals and local leadership rights')

def invitation_active(status:str,expires_at:datetime,now:datetime|None=None)->bool:
    now=now or datetime.now(timezone.utc)
    return status=='pending' and expires_at.tzinfo is not None and expires_at>now
