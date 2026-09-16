"""Golden sample set for the model-bound skills.

A golden is a recorded example of *correct* output for one SKILL.md contract.
It serves three purposes:

1. **Shape lock** - a provider swap that changes the JSON structure shows up as
   a failing diff rather than a silent downstream break.
2. **Guardrail corpus** - every golden must pass its own contract's guardrails,
   so the rule set is continuously exercised against realistic content.
3. **Rollout baseline** - :mod:`tools/run_golden_set.py` replays the set against
   a live provider and diffs the result against these files.

Two tiers exist. ``structural`` goldens lock the output shape only.
``curated`` goldens are hand-authored with real domain content, so a provider
that produces the right shape but wrong *meaning* is still caught.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

GOLDEN_ROOT = Path(__file__).with_name("data") / "golden"

Payload = dict[str, Any]


class GoldenSetError(ValueError):
    """Raised when a golden fixture is malformed."""


@dataclass(frozen=True)
class GoldenCase:
    skill_id: str
    skill_name: str
    skill_version: str
    batch: int
    tier: str
    notes: str
    input: Payload
    expected_output_keys: tuple[str, ...]
    golden_output: Payload
    source_path: str = ""

    @property
    def batch_key(self) -> str:
        return f"batch{self.batch:02d}"

    @property
    def curated(self) -> bool:
        return self.tier == "curated"

    def as_dict(self) -> Payload:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "skill_version": self.skill_version,
            "batch": self.batch,
            "tier": self.tier,
            "notes": self.notes,
            "input": self.input,
            "expected_output_keys": list(self.expected_output_keys),
            "golden_output": self.golden_output,
        }


REQUIRED_FIELDS = (
    "skill_id",
    "skill_name",
    "skill_version",
    "batch",
    "tier",
    "input",
    "expected_output_keys",
    "golden_output",
)

VALID_TIERS = frozenset({"structural", "curated"})


def load_case(path: Path) -> GoldenCase:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GoldenSetError(f"{path}: invalid JSON ({exc})") from exc

    missing = [field_name for field_name in REQUIRED_FIELDS if field_name not in raw]
    if missing:
        raise GoldenSetError(f"{path}: missing fields {missing}")
    if raw["tier"] not in VALID_TIERS:
        raise GoldenSetError(f"{path}: unknown tier {raw['tier']!r}")

    declared = sorted(raw["expected_output_keys"])
    actual = sorted(raw["golden_output"])
    if declared != actual:
        raise GoldenSetError(
            f"{path}: expected_output_keys {declared} != golden_output keys {actual}"
        )

    return GoldenCase(
        skill_id=raw["skill_id"],
        skill_name=raw["skill_name"],
        skill_version=raw["skill_version"],
        batch=int(raw["batch"]),
        tier=raw["tier"],
        notes=raw.get("notes", ""),
        input=raw["input"],
        expected_output_keys=tuple(declared),
        golden_output=raw["golden_output"],
        source_path=str(path.name),
    )


# --- structural diffing -----------------------------------------------------

def shape_of(value: Any) -> Any:
    """Reduce a payload to its structure, discarding leaf values."""

    if isinstance(value, dict):
        return {key: shape_of(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [shape_of(value[0])] if value else []
    return type(value).__name__


def diff_shape(expected: Any, actual: Any, path: str = "") -> list[str]:
    """Report structural divergences between a golden and a live result."""

    problems: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path or '<root>'}: expected object, got {type(actual).__name__}"]
        for key in expected:
            if key not in actual:
                problems.append(f"{path}.{key}".lstrip(".") + ": missing")
            else:
                problems += diff_shape(expected[key], actual[key], f"{path}.{key}".lstrip("."))
        for key in actual:
            if key not in expected:
                problems.append(f"{path}.{key}".lstrip(".") + ": unexpected")
        return problems
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path or '<root>'}: expected array, got {type(actual).__name__}"]
        if expected and actual:
            problems += diff_shape(expected[0], actual[0], f"{path}[0]")
        elif expected and not actual:
            problems.append(f"{path or '<root>'}: expected non-empty array")
        return problems
    if type(expected).__name__ != type(actual).__name__:
        problems.append(
            f"{path or '<root>'}: expected {type(expected).__name__}, got {type(actual).__name__}"
        )
    return problems


@dataclass
class GoldenResult:
    skill_id: str
    tier: str
    status: str
    shape_diffs: list[str] = field(default_factory=list)
    guardrail_violations: list[str] = field(default_factory=list)
    message: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "ok" and not self.shape_diffs and not self.guardrail_violations

    def as_dict(self) -> Payload:
        return {
            "skill_id": self.skill_id,
            "tier": self.tier,
            "status": self.status,
            "passed": self.passed,
            "shape_diffs": self.shape_diffs,
            "guardrail_violations": self.guardrail_violations,
            "message": self.message,
        }


class GoldenSet:
    """The loaded golden corpus, plus helpers to replay it."""

    def __init__(self, root: Path = GOLDEN_ROOT) -> None:
        self.root = root
        self.cases: dict[str, GoldenCase] = {}

    def load(self) -> "GoldenSet":
        if not self.root.exists():
            raise GoldenSetError(f"golden root not found: {self.root}")
        cases: dict[str, GoldenCase] = {}
        for path in sorted(self.root.glob("batch*/*.json")):
            case = load_case(path)
            if case.skill_id in cases:
                raise GoldenSetError(f"duplicate golden for {case.skill_id}")
            cases[case.skill_id] = case
        self.cases = cases
        return self

    # -- access ----------------------------------------------------------

    def __len__(self) -> int:
        return len(self.cases)

    def __iter__(self) -> Iterable[GoldenCase]:
        return iter(self.cases.values())

    def __contains__(self, skill_id: object) -> bool:
        return skill_id in self.cases

    def get(self, skill_id: str) -> GoldenCase:
        try:
            return self.cases[skill_id]
        except KeyError as exc:
            raise KeyError(f"no golden for skill_id: {skill_id}") from exc

    def for_batch(self, batch: int | str) -> list[GoldenCase]:
        key = batch if isinstance(batch, str) else f"batch{batch:02d}"
        return [case for case in self.cases.values() if case.batch_key == key]

    def curated(self) -> list[GoldenCase]:
        return [case for case in self.cases.values() if case.curated]

    # -- replay ----------------------------------------------------------

    def replies(self) -> dict[str, Payload]:
        """Mapping suitable for ``ScriptedAdapter``."""

        return {case.skill_id: case.golden_output for case in self.cases.values()}

    def scripted_adapter(self):
        from .model_adapter import ScriptedAdapter

        return ScriptedAdapter(self.replies())

    def run(self, runtime, *, skill_ids: Iterable[str] | None = None) -> list[GoldenResult]:
        """Replay the corpus through a runtime and diff against the goldens."""

        selected = list(skill_ids) if skill_ids is not None else list(self.cases)
        results: list[GoldenResult] = []
        for skill_id in selected:
            case = self.get(skill_id)
            outcome = runtime.invoke(case.skill_id, case.input)
            violations = [
                finding["guardrail"]
                for finding in outcome.guardrail_findings
                if finding["status"] == "violation"
            ]
            diffs = (
                diff_shape(case.golden_output, outcome.outputs)
                if outcome.status == "ok"
                else []
            )
            results.append(
                GoldenResult(
                    skill_id=case.skill_id,
                    tier=case.tier,
                    status=outcome.status,
                    shape_diffs=diffs,
                    guardrail_violations=violations,
                    message=outcome.message,
                )
            )
        return results

    def summary(self) -> Payload:
        by_batch: dict[str, int] = {}
        for case in self.cases.values():
            by_batch[case.batch_key] = by_batch.get(case.batch_key, 0) + 1
        return {
            "total": len(self.cases),
            "curated": len(self.curated()),
            "structural": len(self.cases) - len(self.curated()),
            "by_batch": dict(sorted(by_batch.items())),
        }


@lru_cache(maxsize=1)
def get_golden_set() -> GoldenSet:
    return GoldenSet().load()
