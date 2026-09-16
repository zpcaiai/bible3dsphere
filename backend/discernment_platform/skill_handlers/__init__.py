"""Native handler bindings for the SKILL.md contracts.

Importing this package registers every native binding with
``skill_runtime.handler``.  Skills without a native binding fall through to the
runtime's contract binding (rendered prompt + declared output envelope), which
never fabricates a result.
"""

from __future__ import annotations

from . import (  # noqa: F401
    batch01,
    batch03,
    batch04,
    batch05,
    batch06,
    batch07,
    batch08,
    batch09,
    batch10,
)

__all__ = [
    "batch01",
    "batch03",
    "batch04",
    "batch05",
    "batch06",
    "batch07",
    "batch08",
    "batch09",
    "batch10",
]
