"""SKILL.md contract parsing and skill_id routing.

Every runtime skill shipped in Batches 01-10 is a versioned markdown contract
under ``data/skills/batchNN/<n>_<skill-id>/SKILL.md``.  This module turns those
documents into validated :class:`SkillContract` objects and exposes them by
``skill_id`` so the runtime can dispatch to them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

DATA_ROOT = Path(__file__).with_name("data")
SKILLS_ROOT = DATA_ROOT / "skills"

FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
SECTION_RE = re.compile(r"^# (.+?)$", re.MULTILINE)

REQUIRED_FRONT_MATTER = ("id", "name", "version", "batch", "type")
REQUIRED_SECTIONS = (
    "Purpose",
    "Inputs",
    "Outputs",
    "Processing Contract",
    "Guardrails",
    "Failure Handling",
    "Acceptance Tests",
)
OPTIONAL_SECTIONS = ("Trigger", "Prompt Contract", "Evidence and Uncertainty")

EXPECTED_SKILL_COUNTS: dict[str, int] = {
    "batch01": 10,
    "batch03": 20,
    "batch04": 20,
    "batch05": 20,
    "batch06": 20,
    "batch07": 20,
    "batch08": 20,
    "batch09": 20,
    "batch10": 24,
}
EXPECTED_TOTAL_SKILLS = sum(EXPECTED_SKILL_COUNTS.values())

_BULLET_RE = re.compile(r"^\s*(?:[-*]\s+|\d+\.\s+)(.*)$")


class SkillContractError(ValueError):
    """Raised when a SKILL.md does not satisfy the contract format."""


@dataclass(frozen=True)
class SkillContract:
    """A parsed, validated SKILL.md."""

    skill_id: str
    name: str
    version: str
    batch: int
    skill_type: str
    purpose: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    processing_contract: tuple[str, ...]
    guardrails: tuple[str, ...]
    failure_handling: tuple[str, ...]
    acceptance_tests: tuple[str, ...]
    trigger: str = ""
    prompt_contract: str = ""
    evidence_and_uncertainty: str = ""
    requires: str = ""
    source_path: str = ""
    order: int = 0
    sections: dict[str, str] = field(default_factory=dict, repr=False)

    @property
    def batch_key(self) -> str:
        return f"batch{self.batch:02d}"

    @property
    def always_on(self) -> bool:
        return "always-on" in self.skill_type

    @property
    def is_deterministic(self) -> bool:
        return self.skill_type.startswith("deterministic") or self.skill_type == "composer"

    def as_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "version": self.version,
            "batch": self.batch,
            "type": self.skill_type,
            "order": self.order,
            "purpose": self.purpose,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "processing_contract": list(self.processing_contract),
            "guardrails": list(self.guardrails),
            "failure_handling": list(self.failure_handling),
            "acceptance_tests": list(self.acceptance_tests),
            "trigger": self.trigger,
            "prompt_contract": self.prompt_contract,
            "requires": self.requires,
            "always_on": self.always_on,
            "source_path": self.source_path,
        }


def _split_front_matter(text: str, source: str) -> tuple[dict[str, str], str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        raise SkillContractError(f"{source}: missing YAML front matter")
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    missing = [key for key in REQUIRED_FRONT_MATTER if key not in meta]
    if missing:
        raise SkillContractError(f"{source}: front matter missing {missing}")
    return meta, text[match.end():]


def _split_sections(body: str, source: str) -> dict[str, str]:
    headings = list(SECTION_RE.finditer(body))
    if not headings:
        raise SkillContractError(f"{source}: no '# Section' headings found")
    sections: dict[str, str] = {}
    for index, heading in enumerate(headings):
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        sections[heading.group(1).strip()] = body[start:end].strip()
    missing = [name for name in REQUIRED_SECTIONS if name not in sections]
    if missing:
        raise SkillContractError(f"{source}: missing sections {missing}")
    return sections


def as_items(block: str) -> tuple[str, ...]:
    """Normalise a section body into discrete items.

    Handles bullet lists, numbered lists, fenced blocks and free prose
    (split on sentence terminators) so that every contract yields structured
    items regardless of how the batch authored it.
    """

    if not block:
        return ()
    cleaned = re.sub(r"```.*?```", lambda m: m.group(0).strip("`"), block, flags=re.DOTALL)
    lines = [line for line in cleaned.splitlines()]
    bullets = [m.group(1).strip() for m in (_BULLET_RE.match(line) for line in lines) if m]
    if bullets:
        return tuple(item for item in bullets if item)
    prose = " ".join(line.strip() for line in lines if line.strip())
    parts = [part.strip() for part in re.split(r"[。；;]\s*|\n", prose) if part.strip()]
    return tuple(parts) if parts else (prose,)


def parse_skill_md(text: str, source_path: str = "<memory>", order: int = 0) -> SkillContract:
    meta, body = _split_front_matter(text, source_path)
    sections = _split_sections(body, source_path)
    try:
        batch = int(meta["batch"])
    except ValueError as exc:  # pragma: no cover - defensive
        raise SkillContractError(f"{source_path}: batch must be an integer") from exc

    purpose = sections["Purpose"].strip()
    if not purpose:
        raise SkillContractError(f"{source_path}: Purpose section is empty")

    return SkillContract(
        skill_id=meta["id"],
        name=meta["name"],
        version=meta["version"],
        batch=batch,
        skill_type=meta["type"],
        purpose=purpose,
        inputs=as_items(sections["Inputs"]),
        outputs=as_items(sections["Outputs"]),
        processing_contract=as_items(sections["Processing Contract"]),
        guardrails=as_items(sections["Guardrails"]),
        failure_handling=as_items(sections["Failure Handling"]),
        acceptance_tests=as_items(sections["Acceptance Tests"]),
        trigger=sections.get("Trigger", "").strip(),
        prompt_contract=sections.get("Prompt Contract", "").strip(),
        evidence_and_uncertainty=sections.get("Evidence and Uncertainty", "").strip(),
        requires=meta.get("requires", ""),
        source_path=source_path,
        order=order,
        sections=sections,
    )


def load_skill_file(path: Path, root: Path | None = None) -> SkillContract:
    source = str(path.relative_to(root)) if root else str(path)
    match = re.match(r"(\d+)_", path.parent.name)
    order = int(match.group(1)) if match else 0
    return parse_skill_md(path.read_text(encoding="utf-8"), source, order)


class SkillRegistry:
    """Loads every SKILL.md and routes by ``skill_id``."""

    def __init__(self, root: Path = SKILLS_ROOT) -> None:
        self.root = root
        self.skills: dict[str, SkillContract] = {}
        self._by_batch: dict[str, list[SkillContract]] = {}

    # --- loading -------------------------------------------------------

    def load(self, *, strict: bool = True) -> "SkillRegistry":
        if not self.root.exists():
            raise SkillContractError(f"skills root not found: {self.root}")
        skills: dict[str, SkillContract] = {}
        for path in sorted(self.root.glob("batch*/*/SKILL.md")):
            contract = load_skill_file(path, self.root.parent.parent)
            if contract.skill_id in skills:
                raise SkillContractError(f"Duplicate skill id: {contract.skill_id}")
            skills[contract.skill_id] = contract
        self.skills = skills
        self._by_batch = {}
        for contract in skills.values():
            self._by_batch.setdefault(contract.batch_key, []).append(contract)
        for contracts in self._by_batch.values():
            contracts.sort(key=lambda c: (c.order, c.skill_id))
        if strict:
            self.validate()
        return self

    def validate(self) -> None:
        for batch_key, expected in EXPECTED_SKILL_COUNTS.items():
            found = len(self._by_batch.get(batch_key, []))
            if found != expected:
                raise SkillContractError(
                    f"Expected {expected} skills in {batch_key}, found {found}"
                )
        if len(self.skills) != EXPECTED_TOTAL_SKILLS:
            raise SkillContractError(
                f"Expected {EXPECTED_TOTAL_SKILLS} runtime skills, found {len(self.skills)}"
            )
        for contract in self.skills.values():
            if contract.batch_key not in EXPECTED_SKILL_COUNTS:
                raise SkillContractError(
                    f"{contract.skill_id}: unexpected batch {contract.batch}"
                )
            for name, values in (
                ("inputs", contract.inputs),
                ("outputs", contract.outputs),
                ("processing_contract", contract.processing_contract),
                ("guardrails", contract.guardrails),
                ("failure_handling", contract.failure_handling),
                ("acceptance_tests", contract.acceptance_tests),
            ):
                if not values:
                    raise SkillContractError(f"{contract.skill_id}: empty {name}")

    # --- routing -------------------------------------------------------

    def __contains__(self, skill_id: object) -> bool:
        return skill_id in self.skills

    def __len__(self) -> int:
        return len(self.skills)

    def __iter__(self) -> Iterable[SkillContract]:
        return iter(self.skills.values())

    def get(self, skill_id: str) -> SkillContract:
        try:
            return self.skills[skill_id]
        except KeyError as exc:
            raise KeyError(f"Unknown skill_id: {skill_id}") from exc

    def for_batch(self, batch: int | str) -> list[SkillContract]:
        key = batch if isinstance(batch, str) else f"batch{batch:02d}"
        return list(self._by_batch.get(key, []))

    def pipeline(self, batch: int | str) -> list[str]:
        """Skill ids for a batch in declared execution order, always-on first."""

        contracts = self.for_batch(batch)
        always_on = [c for c in contracts if c.always_on]
        rest = [c for c in contracts if not c.always_on]
        return [c.skill_id for c in always_on + rest]

    def search(self, term: str) -> list[SkillContract]:
        needle = term.lower()
        return [
            c
            for c in self.skills.values()
            if needle in c.skill_id.lower()
            or needle in c.name.lower()
            or needle in c.purpose.lower()
        ]

    def catalog(self) -> dict[str, Any]:
        return {
            "total": len(self.skills),
            "by_batch": {
                key: [c.skill_id for c in contracts]
                for key, contracts in sorted(self._by_batch.items())
            },
            "counts": {key: len(v) for key, v in sorted(self._by_batch.items())},
            "always_on": [c.skill_id for c in self.skills.values() if c.always_on],
        }


@lru_cache(maxsize=1)
def get_skill_registry() -> SkillRegistry:
    return SkillRegistry().load()
