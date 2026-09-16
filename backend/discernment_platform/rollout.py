"""Staged rollout gating for model-bound skills.

Native skills are unaffected - they are deterministic Python and always run.
This module governs only the 82 contract-bound skills, i.e. exactly the ones
whose output comes from a language model.

Four stages, in increasing order of trust:

``disabled``     the model is not called at all; the runtime reports
                 ``blocked_by_rollout`` so the caller cannot mistake silence
                 for a clean result
``shadow``       the model runs and the output is recorded, but it is returned
                 as ``shadow`` - explicitly non-authoritative, for comparison
                 against human or native output during evaluation
``pilot``        the model runs and the output is authoritative, but every
                 result is flagged for human review
``production``   the model runs and the output is authoritative

The shipped default plan follows the agreed rollout order: the low-risk
analysis batches go to pilot first, the pastoral and safety batches stay in
shadow, and the release gate stays in shadow because its C3/C4 controls may
never be certified by a model on its own.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).with_name("data") / "config" / "rollout.json"


class Stage(str, Enum):
    DISABLED = "disabled"
    SHADOW = "shadow"
    PILOT = "pilot"
    PRODUCTION = "production"

    @property
    def rank(self) -> int:
        return list(Stage).index(self)

    @property
    def runs_model(self) -> bool:
        return self is not Stage.DISABLED

    @property
    def authoritative(self) -> bool:
        return self in {Stage.PILOT, Stage.PRODUCTION}

    @property
    def requires_human_review(self) -> bool:
        return self in {Stage.SHADOW, Stage.PILOT}


#: Rollout order agreed for first release: analysis batches first, pastoral and
#: safety batches held in shadow, release gate never model-authoritative.
DEFAULT_PLAN: dict[str, Stage] = {
    "batch01": Stage.PRODUCTION,  # fully native; listed for completeness
    "batch03": Stage.PILOT,       # 网红热点分析 - public material, low pastoral risk
    "batch04": Stage.PILOT,       # 自高自义模型 - hypotheses only, never verdicts
    "batch05": Stage.SHADOW,      # 苏格拉底对话 - speaks directly to the user
    "batch06": Stage.SHADOW,      # 律法—福音路径 - doctrinal content
    "batch07": Stage.SHADOW,      # Formation Twin - longitudinal personal data
    "batch08": Stage.SHADOW,      # 牧者协作 - safeguarding and access control
    "batch09": Stage.PILOT,       # 释经与证据 - citation-bound, auditable
    "batch10": Stage.SHADOW,      # release gate - C3/C4 need human sign-off
}

#: Batches whose skills may never be certified by a model without a human.
HUMAN_SIGNOFF_BATCHES = frozenset({"batch08", "batch10"})

ENV_PLAN = "DISCERNMENT_ROLLOUT_PLAN"
ENV_BATCH_PREFIX = "DISCERNMENT_ROLLOUT_"


class RolloutError(ValueError):
    """Raised when a rollout configuration is invalid."""


@dataclass(frozen=True)
class RolloutDecision:
    skill_id: str
    batch_key: str
    stage: Stage
    allowed: bool
    authoritative: bool
    human_review_required: bool
    human_signoff_required: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "batch_key": self.batch_key,
            "stage": self.stage.value,
            "allowed": self.allowed,
            "authoritative": self.authoritative,
            "human_review_required": self.human_review_required,
            "human_signoff_required": self.human_signoff_required,
            "reason": self.reason,
        }


class RolloutPolicy:
    """Maps a skill to its rollout stage."""

    def __init__(
        self,
        plan: dict[str, Stage] | None = None,
        *,
        overrides: dict[str, Stage] | None = None,
        name: str = "custom",
    ) -> None:
        # ``None`` means "use the shipped plan"; an explicitly empty dict means
        # empty, and every batch then falls through to the SHADOW default.
        self.plan = dict(DEFAULT_PLAN if plan is None else plan)
        self.overrides = dict({} if overrides is None else overrides)
        self.name = name

    # -- constructors ----------------------------------------------------

    @classmethod
    def staged(cls) -> "RolloutPolicy":
        """The shipped rollout plan."""

        return cls(DEFAULT_PLAN, name="staged")

    @classmethod
    def unrestricted(cls) -> "RolloutPolicy":
        """Everything in production. Used by tests and by single-tenant dev."""

        return cls({key: Stage.PRODUCTION for key in DEFAULT_PLAN}, name="unrestricted")

    @classmethod
    def all_disabled(cls) -> "RolloutPolicy":
        return cls({key: Stage.DISABLED for key in DEFAULT_PLAN}, name="all_disabled")

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, name: str = "file") -> "RolloutPolicy":
        plan = dict(DEFAULT_PLAN)
        for key, value in (raw.get("batches") or {}).items():
            plan[key] = _stage(value, where=f"batches.{key}")
        overrides = {
            skill_id: _stage(value, where=f"skills.{skill_id}")
            for skill_id, value in (raw.get("skills") or {}).items()
        }
        return cls(plan, overrides=overrides, name=raw.get("name", name))

    @classmethod
    def from_file(cls, path: Path = CONFIG_PATH) -> "RolloutPolicy":
        if not path.exists():
            raise RolloutError(f"rollout config not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RolloutError(f"{path}: invalid JSON ({exc})") from exc
        return cls.from_dict(raw, name=str(path.name))

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "RolloutPolicy":
        env = dict(os.environ if env is None else env)
        setting = (env.get(ENV_PLAN) or "staged").strip()
        lowered = setting.lower()
        if lowered in {"staged", "", "default"}:
            policy = cls.staged()
        elif lowered in {"unrestricted", "all", "production"}:
            policy = cls.unrestricted()
        elif lowered in {"disabled", "off", "none"}:
            policy = cls.all_disabled()
        else:
            policy = cls.from_file(Path(setting))

        for key, value in env.items():
            if not key.startswith(ENV_BATCH_PREFIX) or key == ENV_PLAN:
                continue
            batch_key = key[len(ENV_BATCH_PREFIX) :].lower()
            if not batch_key.startswith("batch"):
                continue
            policy.plan[batch_key] = _stage(value, where=key)
        return policy

    # -- decisions -------------------------------------------------------

    def stage_for(self, contract) -> Stage:
        if contract.skill_id in self.overrides:
            return self.overrides[contract.skill_id]
        return self.plan.get(contract.batch_key, Stage.SHADOW)

    def decide(self, contract) -> RolloutDecision:
        stage = self.stage_for(contract)
        signoff = contract.batch_key in HUMAN_SIGNOFF_BATCHES
        if stage is Stage.DISABLED:
            reason = f"{contract.batch_key} 处于 disabled 阶段，未启用模型绑定"
        elif stage is Stage.SHADOW:
            reason = f"{contract.batch_key} 处于 shadow 阶段，模型输出仅作对照，不作为权威结果"
        elif stage is Stage.PILOT:
            reason = f"{contract.batch_key} 处于 pilot 阶段，输出有效但每条都需人工复核"
        else:
            reason = f"{contract.batch_key} 已进入 production 阶段"
        if signoff and stage.authoritative:
            reason += "；该批次的高危控制项仍需人工签署，模型不得自证"
        return RolloutDecision(
            skill_id=contract.skill_id,
            batch_key=contract.batch_key,
            stage=stage,
            allowed=stage.runs_model,
            authoritative=stage.authoritative,
            human_review_required=stage.requires_human_review or signoff,
            human_signoff_required=signoff,
            reason=reason,
        )

    # -- reporting -------------------------------------------------------

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "batches": {key: stage.value for key, stage in sorted(self.plan.items())},
            "skills": {key: stage.value for key, stage in sorted(self.overrides.items())},
        }

    def promote(self, batch_key: str, stage: Stage | str) -> "RolloutPolicy":
        """Return a copy with one batch moved to a new stage."""

        plan = dict(self.plan)
        plan[batch_key] = _stage(stage, where=batch_key)
        return RolloutPolicy(plan, overrides=self.overrides, name=f"{self.name}+{batch_key}")


def _stage(value: Stage | str, *, where: str) -> Stage:
    if isinstance(value, Stage):
        return value
    try:
        return Stage(str(value).strip().lower())
    except ValueError as exc:
        raise RolloutError(
            f"{where}: unknown rollout stage {value!r}; expected one of "
            f"{[stage.value for stage in Stage]}"
        ) from exc


@lru_cache(maxsize=1)
def get_policy() -> RolloutPolicy:
    return RolloutPolicy.from_env()
