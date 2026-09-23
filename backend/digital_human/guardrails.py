from __future__ import annotations

from .contracts import DigitalHumanResponse
from .scripture import resolve_reference

FORBIDDEN_REVELATION_MARKERS = (
    "神现在告诉你", "神要我告诉你", "我奉神告诉你", "神已经明确告诉我你",
)


def validate_response(response: DigitalHumanResponse) -> DigitalHumanResponse:
    text = f"{response.spokenText}\n{response.displayText}"
    if any(marker in text for marker in FORBIDDEN_REVELATION_MARKERS):
        raise ValueError("fabricated divine-revelation pattern detected")
    for item in response.references:
        if item.sourceType == "SCRIPTURE" and not resolve_reference(item.locator):
            raise ValueError(f"unresolvable scripture reference: {item.locator}")
    return response
