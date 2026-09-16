"""Deterministic, evidence-governed discernment runtime (Batches 01-10)."""

from .dialogue import DialogueEngine
from .engine import DiscernmentEngine
from .gospel import GospelPathEngine
from .registry import DiscernmentRegistry, get_registry
from .skills import (
    SkillContract,
    SkillContractError,
    SkillRegistry,
    get_skill_registry,
    parse_skill_md,
)
from .skill_runtime import (
    NullAdapter,
    SkillInvocationError,
    SkillResult,
    SkillRuntime,
    get_runtime,
    handler,
)
from .model_adapter import (
    AnthropicAdapter,
    GeminiAdapter,
    LocalOpenAIAdapter,
    OpenAIAdapter,
    RecordingAdapter,
    ScriptedAdapter,
    build_adapter,
    build_adapter_from_env,
)
from .golden import GoldenCase, GoldenSet, GoldenSetError, diff_shape, get_golden_set
from .rollout import RolloutError, RolloutPolicy, Stage, get_policy

__all__ = [
    "AnthropicAdapter",
    "DialogueEngine",
    "GeminiAdapter",
    "GoldenCase",
    "GoldenSet",
    "GoldenSetError",
    "RolloutError",
    "RolloutPolicy",
    "Stage",
    "diff_shape",
    "get_golden_set",
    "get_policy",
    "DiscernmentEngine",
    "DiscernmentRegistry",
    "GospelPathEngine",
    "LocalOpenAIAdapter",
    "NullAdapter",
    "OpenAIAdapter",
    "RecordingAdapter",
    "ScriptedAdapter",
    "SkillContract",
    "SkillContractError",
    "SkillInvocationError",
    "SkillRegistry",
    "SkillResult",
    "SkillRuntime",
    "build_adapter",
    "build_adapter_from_env",
    "get_registry",
    "get_runtime",
    "get_skill_registry",
    "handler",
    "parse_skill_md",
]
