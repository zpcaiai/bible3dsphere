from __future__ import annotations

import json
from pathlib import Path
from .models import CertificationControl


class CertificationRegistry:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._controls: dict[str, CertificationControl] = {}

    def load(self) -> "CertificationRegistry":
        for path in self.root.glob("*/pack.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            for raw in payload["controls"]:
                control = CertificationControl.model_validate(raw)
                if control.control_id in self._controls:
                    raise ValueError(f"Duplicate control: {control.control_id}")
                self._controls[control.control_id] = control
        return self

    def get(self, control_id: str) -> CertificationControl:
        return self._controls[control_id]

    def all(self) -> list[CertificationControl]:
        return list(self._controls.values())

    def by_domain(self, domain_id: str) -> list[CertificationControl]:
        return [c for c in self._controls.values() if c.domain_id == domain_id]

    def __len__(self) -> int:
        return len(self._controls)
