from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


DATA_ROOT = Path(__file__).with_name("data")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class DiscernmentRegistry:
    """Loads and validates the versioned assets supplied by Batches 01-10."""

    def __init__(self, root: Path = DATA_ROOT) -> None:
        self.root = root
        self.domain_packs: dict[str, dict[str, Any]] = {}
        self.hypothesis_packs: dict[str, dict[str, Any]] = {}
        self.question_packs: dict[str, dict[str, Any]] = {}
        self.doctrine_packs: dict[str, dict[str, Any]] = {}
        self.formation_packs: dict[str, dict[str, Any]] = {}
        self.role_packs: dict[str, dict[str, Any]] = {}
        self.knowledge_packs: dict[str, dict[str, Any]] = {}
        self.certification_packs: dict[str, dict[str, Any]] = {}
        self.manifests: dict[str, dict[str, Any]] = {}

    def load(self) -> "DiscernmentRegistry":
        self.domain_packs = self._load_named("domain_packs/*/pack.json")
        self.hypothesis_packs = self._load_named("hypothesis_packs/*/pack.json")
        self.doctrine_packs = self._load_named("doctrine_packs/*/pack.json")
        self.formation_packs = self._load_named("formation_packs/*/pack.json")
        self.role_packs = self._load_named("role_packs/*/pack.json")
        self.knowledge_packs = self._load_named("knowledge_packs/*/pack.json")
        self.certification_packs = self._load_named("certification_packs/*/pack.json")
        self.manifests = {
            path.stem: _load(path) for path in sorted(self.root.glob("manifests/batch*.json"))
        }
        question_files = [path for path in sorted(self.root.glob("question_packs/*.json")) if path.name != "registry.json"]
        self.question_packs = {data["pack_id"]: data for data in map(_load, question_files)}
        self.validate()
        return self

    def _load_named(self, pattern: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for path in sorted(self.root.glob(pattern)):
            item = _load(path)
            pack_id = item["id"]
            if pack_id in result:
                raise ValueError(f"Duplicate discernment pack id: {pack_id}")
            item["_asset_dir"] = str(path.parent)
            result[pack_id] = item
        return result

    def related_asset(self, pack: dict[str, Any], filename: str, fallback: Any) -> Any:
        path = Path(pack["_asset_dir"]) / filename
        return _load(path) if path.exists() else fallback

    def validate(self) -> None:
        expected = {
            "domain": (self.domain_packs, 32),
            "hypothesis": (self.hypothesis_packs, 9),
            "question": (self.question_packs, 8),
            "doctrine": (self.doctrine_packs, 10),
            "formation": (self.formation_packs, 8),
            "role": (self.role_packs, 8),
            "knowledge": (self.knowledge_packs, 12),
            "certification": (self.certification_packs, 12),
        }
        for kind, (packs, count) in expected.items():
            if len(packs) != count:
                raise ValueError(f"Expected {count} {kind} packs, found {len(packs)}")
        for pack in self.domain_packs.values():
            required = {"version", "cluster", "common_grace", "worldview", "detection", "gospel_summary"}
            if missing := required - set(pack):
                raise ValueError(f"Domain pack {pack['id']} missing {sorted(missing)}")
            if len(pack["common_grace"]) < 3 or len(pack.get("pride_hypotheses", [])) < 3:
                raise ValueError(f"Domain pack {pack['id']} is incomplete")
        for pack in self.hypothesis_packs.values():
            required = {"version", "created_good", "signals", "alternative_explanations", "counter_evidence", "gospel_bridge"}
            if missing := required - set(pack):
                raise ValueError(f"Hypothesis pack {pack['id']} missing {sorted(missing)}")
        for pack in self.doctrine_packs.values():
            required = {"version", "tier", "core_claims", "pastoral_applications"}
            if missing := required - set(pack):
                raise ValueError(f"Doctrine pack {pack['id']} missing {sorted(missing)}")
        for pack in self.formation_packs.values():
            if missing := {"version", "focus", "healthy_fruits", "warning_signals", "evidence", "safety"} - set(pack):
                raise ValueError(f"Formation pack {pack['id']} missing {sorted(missing)}")
        for pack in self.role_packs.values():
            if missing := {"version", "permissions", "prohibitions", "default_scope"} - set(pack):
                raise ValueError(f"Role pack {pack['id']} missing {sorted(missing)}")
        for pack in self.knowledge_packs.values():
            if missing := {"version", "scope", "capabilities", "risks", "safety"} - set(pack):
                raise ValueError(f"Knowledge pack {pack['id']} missing {sorted(missing)}")
        control_ids: set[str] = set()
        for pack in self.certification_packs.values():
            if missing := {"version", "controls"} - set(pack):
                raise ValueError(f"Certification pack {pack['id']} missing {sorted(missing)}")
            for control in pack["controls"]:
                control_id = control["control_id"]
                if control_id in control_ids:
                    raise ValueError(f"Duplicate certification control: {control_id}")
                control_ids.add(control_id)
        if len(control_ids) != 58:
            raise ValueError(f"Expected 58 certification controls, found {len(control_ids)}")
        if len(self.manifests) != 10:
            raise ValueError(f"Expected 10 batch manifests, found {len(self.manifests)}")
        for number in range(1, 11):
            manifest = self.manifests[f"batch{number:02d}"]
            if manifest.get("batch") != number:
                raise ValueError(f"Batch manifest mismatch for batch{number:02d}")
        self._validate_assets_against_schemas()

    def _validate_assets_against_schemas(self) -> None:
        checks = [
            (self.domain_packs.values(), "batch02/domain_pack.schema.json"),
            (self.hypothesis_packs.values(), "batch04/hypothesis_pack.schema.json"),
            (self.doctrine_packs.values(), "batch06/doctrine_pack.schema.json"),
        ]
        for packs, relative_schema in checks:
            schema = _load(self.root / "schemas" / relative_schema)
            validator = Draft202012Validator(schema)
            for pack in packs:
                instance = {key: value for key, value in pack.items() if key != "_asset_dir"}
                errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
                if errors:
                    joined = "; ".join(error.message for error in errors[:5])
                    raise ValueError(f"Pack {pack['id']} failed {relative_schema}: {joined}")
        control_schema = _load(self.root / "schemas" / "batch10" / "certification_control.schema.json")
        control_validator = Draft202012Validator(control_schema)
        for pack in self.certification_packs.values():
            for control in pack["controls"]:
                errors = sorted(control_validator.iter_errors(control), key=lambda error: list(error.path))
                if errors:
                    joined = "; ".join(error.message for error in errors[:5])
                    raise ValueError(f"Control {control['control_id']} failed certification schema: {joined}")

    def validate_instance(self, instance: dict[str, Any], *, batch: str, schema_name: str) -> list[str]:
        schema = _load(self.root / "schemas" / batch / schema_name)
        validator = Draft202012Validator(schema)
        return [error.message for error in sorted(validator.iter_errors(instance), key=lambda error: list(error.path))]

    def catalog(self) -> dict[str, Any]:
        return {
            "versions": {key: manifest["version"] for key, manifest in self.manifests.items()},
            "counts": {
                "domain_packs": len(self.domain_packs),
                "hypothesis_packs": len(self.hypothesis_packs),
                "question_packs": len(self.question_packs),
                "doctrine_packs": len(self.doctrine_packs),
                "formation_packs": len(self.formation_packs),
                "role_packs": len(self.role_packs),
                "knowledge_packs": len(self.knowledge_packs),
                "certification_packs": len(self.certification_packs),
                "certification_controls": sum(len(pack["controls"]) for pack in self.certification_packs.values()),
            },
            "domain_packs": [
                {"id": p["id"], "name": p["name"], "version": p["version"], "cluster": p["cluster"], "fair_definition": p["fair_definition"]}
                for p in sorted(self.domain_packs.values(), key=lambda item: (item["cluster"], item["name"]))
            ],
            "hypothesis_packs": [
                {"id": p["id"], "name": p["name_zh"], "version": p["version"], "fair_definition": p["fair_definition"]}
                for p in sorted(self.hypothesis_packs.values(), key=lambda item: item["name_zh"])
            ],
            "doctrine_packs": [
                {"id": p["id"], "name": p["name_zh"], "version": p["version"], "tier": p["tier"]}
                for p in self.ordered_doctrine_packs()
            ],
            "formation_packs": self._catalog_items(self.formation_packs),
            "role_packs": self._catalog_items(self.role_packs),
            "knowledge_packs": self._catalog_items(self.knowledge_packs),
            "certification_packs": [
                {"id": p["id"], "name": p["name_zh"], "version": p["version"], "control_count": len(p["controls"])}
                for p in sorted(self.certification_packs.values(), key=lambda item: item["id"])
            ],
        }

    @staticmethod
    def _catalog_items(packs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {"id": p["id"], "name": p["name_zh"], "version": p["version"]}
            for p in sorted(packs.values(), key=lambda item: item["id"])
        ]

    def ordered_doctrine_packs(self) -> list[dict[str, Any]]:
        order = [
            "creation_order", "sin_and_idolatry", "uses_of_law", "christ_and_atonement",
            "justification_by_faith", "adoption", "union_with_christ",
            "sanctification_by_spirit", "church_community", "eschatological_hope",
        ]
        return [self.doctrine_packs[pack_id] for pack_id in order]


@lru_cache(maxsize=1)
def get_registry() -> DiscernmentRegistry:
    return DiscernmentRegistry().load()
