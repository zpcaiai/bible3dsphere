"""Strong nominal identifiers shared by Mission OS domain services."""

from typing import NewType

MissionId = NewType("MissionId", str)
TenantId = NewType("TenantId", str)
UserId = NewType("UserId", str)
OrganizationId = NewType("OrganizationId", str)
FieldId = NewType("FieldId", str)
PeopleGroupId = NewType("PeopleGroupId", str)
AssessmentId = NewType("AssessmentId", str)
SendingJourneyId = NewType("SendingJourneyId", str)
DeploymentId = NewType("DeploymentId", str)
IncidentId = NewType("IncidentId", str)
