"""EMD-OS pilot gate — 在 PILOT 配置档下关闭分享与小组功能，运行期强制。

`emd_assurance_profiles` 说 PILOT 档 `sharing_allowed = False`。那只是一个声明；
如果同意项照旧提供、牧养摘要接口照旧可调，声明就没有任何约束力。

本模块把配置档变成运行期行为：

    available_consent_scopes()  试点期不提供 EMD_PASTORAL_SHARE / EMD_GROUP_SHARE
    enforce_scope_request()     用户即使直接构造请求也拿不到被关闭的 scope
    guard_feature()             牧养摘要、转介、小组操练接口的统一入口守卫

默认档取环境变量 `EMD_ASSURANCE_PROFILE`，缺省为 PILOT——即默认最保守，
需要显式配置才能开放分享，而不是反过来。
"""
from __future__ import annotations

import os
from typing import Any

from production_governance.emd_assurance_profiles import resolve_profile

from .emotional_maturity import CONSENT_SCOPES


DEFAULT_PROFILE_ENV = "EMD_ASSURANCE_PROFILE"

# 需要「可以对外分享」才能提供的同意项。
SHARING_SCOPES: frozenset[str] = frozenset({"EMD_PASTORAL_SHARE"})
# 需要「可以开小组功能」才能提供的同意项。
GROUP_SCOPES: frozenset[str] = frozenset({"EMD_GROUP_SHARE"})

# 功能 → 需要的能力。
FEATURE_REQUIREMENTS: dict[str, str] = {
    "PASTORAL_SUMMARY": "sharing_allowed",
    "PASTORAL_HANDOFF": "sharing_allowed",
    "EXPORT_FOR_THIRD_PARTY": "sharing_allowed",
    "GROUP_PRACTICE": "group_features_allowed",
    "COMMUNITY_FEEDBACK": "group_features_allowed",
    "PEER_WATCH": "group_features_allowed",
}


class PilotGateError(PermissionError):
    """Raised when a pilot deployment is asked for a capability it is not certified for."""


def active_profile(profile: str | None = None) -> str:
    """Explicit argument wins; otherwise environment; otherwise the safest option."""
    if profile:
        return profile
    return os.environ.get(DEFAULT_PROFILE_ENV) or "PILOT"


def capabilities(profile: str | None = None) -> dict[str, Any]:
    resolved = active_profile(profile)
    settings = resolve_profile(resolved)
    return {
        "profile": resolved,
        "sharing_allowed": bool(settings["sharing_allowed"]),
        "group_features_allowed": bool(settings["group_features_allowed"]),
        "max_certifiable_level": settings["max_certifiable_level"],
        "required_labels": list(settings["required_labels"]),
    }


def available_consent_scopes(profile: str | None = None) -> dict[str, Any]:
    """The consent screen must not offer what the deployment cannot honour."""
    caps = capabilities(profile)
    withheld: dict[str, str] = {}
    offered: dict[str, str] = {}

    for scope, description in CONSENT_SCOPES.items():
        if scope in SHARING_SCOPES and not caps["sharing_allowed"]:
            withheld[scope] = "试点档未认证第三方分享，因此不提供该同意项"
        elif scope in GROUP_SCOPES and not caps["group_features_allowed"]:
            withheld[scope] = "试点档未认证小组功能，因此不提供该同意项"
        else:
            offered[scope] = description

    return {
        "profile": caps["profile"],
        "scopes": offered,
        "withheld_scopes": withheld,
        "independently_withdrawable": True,
        "private_core_scope": "EMD_SELF_ASSESSMENT",
        "note": (
            "试点期不提供分享与小组同意项。这不是暂时隐藏按钮——"
            "即使直接构造请求，这些 scope 也不会被授予。"
        ),
    }


def enforce_scope_request(
    requested_scopes: list[str],
    *,
    profile: str | None = None,
) -> dict[str, Any]:
    """Filter a consent request down to what this deployment may actually grant."""
    available = available_consent_scopes(profile)
    allowed = [scope for scope in requested_scopes if scope in available["scopes"]]
    blocked = [scope for scope in requested_scopes if scope in available["withheld_scopes"]]
    unknown = [
        scope for scope in requested_scopes
        if scope not in available["scopes"] and scope not in available["withheld_scopes"]
    ]
    return {
        "profile": available["profile"],
        "granted_scopes": allowed,
        "blocked_by_profile": blocked,
        "unknown_scopes": unknown,
        "modified": bool(blocked or unknown),
    }


def guard_feature(feature: str, *, profile: str | None = None) -> dict[str, Any]:
    """Raise before a non-certified capability does anything observable."""
    requirement = FEATURE_REQUIREMENTS.get(feature)
    if requirement is None:
        raise PilotGateError(f"unknown feature: {feature}")

    caps = capabilities(profile)
    if not caps[requirement]:
        raise PilotGateError(
            f"{feature} 在 {caps['profile']} 配置档下未认证"
            f"（{requirement}=False，证书上限 {caps['max_certifiable_level']}）"
        )
    return {"feature": feature, "allowed": True, "profile": caps["profile"]}


def feature_matrix(profile: str | None = None) -> dict[str, Any]:
    caps = capabilities(profile)
    return {
        **caps,
        "features": {
            feature: caps[requirement] for feature, requirement in FEATURE_REQUIREMENTS.items()
        },
        "consent_scopes_withheld": sorted(available_consent_scopes(profile)["withheld_scopes"]),
    }
