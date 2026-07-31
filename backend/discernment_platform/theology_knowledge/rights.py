from __future__ import annotations

from .models import RightsStatus


class RightsPolicy:
    def can_embed(self, status: RightsStatus, user_consent: bool = False) -> bool:
        if status in {RightsStatus.PUBLIC_DOMAIN, RightsStatus.OPEN_LICENSE, RightsStatus.LICENSED_INTERNAL}:
            return True
        if status == RightsStatus.USER_OWNED:
            return user_consent
        return False

    def can_generate_from(self, status: RightsStatus) -> bool:
        return status != RightsStatus.PROHIBITED_FOR_GENERATION

    def can_quote(self, status: RightsStatus) -> bool:
        return status not in {
            RightsStatus.METADATA_ONLY,
            RightsStatus.PROHIBITED_FOR_GENERATION,
        }
