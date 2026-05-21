"""Built-in model profiles and resolution (Senna Arc 7–8)."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from mirofish_backend.config import Settings

ProviderType = Literal["openai_compatible", "anthropic"]
ReliabilityLevel = Literal["high", "medium", "low"]
LeakageRiskLevel = Literal["low", "medium", "high"]

LOCAL_LMSTUDIO_DEFAULT_ID = "local_lmstudio_default"
ANTHROPIC_DEFAULT_ID = "anthropic_default"
OPENAI_DEFAULT_ID = "openai_default"
OPENROUTER_DEFAULT_ID = "openrouter_default"

PROFILE_UI_DESCRIPTIONS: dict[str, str] = {
    LOCAL_LMSTUDIO_DEFAULT_ID: "Runs on your local LM Studio server (OpenAI-compatible API).",
    ANTHROPIC_DEFAULT_ID: "Uses the configured Anthropic API model (Claude).",
    OPENAI_DEFAULT_ID: "OpenAI chat completions API (requires API key in environment).",
    OPENROUTER_DEFAULT_ID: "OpenRouter gateway (OpenAI-compatible; requires API key in environment).",
}

HYBRID_ROUTING_LABEL = "Mixed local + Claude"
HYBRID_ROUTING_DESCRIPTION = (
    "Uses Claude on the first turn of each round, then the local model for remaining turns."
)

_BUILTIN_PROFILE_FACTORIES: dict[str, Callable[[Settings], "ModelProfile"]] = {}


def register_builtin_profile(profile_id: str) -> Callable[[Callable[[Settings], ModelProfile]], Callable[[Settings], ModelProfile]]:
    """Register a built-in profile factory (registry pattern, iter-36)."""

    def decorator(fn: Callable[[Settings], ModelProfile]) -> Callable[[Settings], ModelProfile]:
        _BUILTIN_PROFILE_FACTORIES[profile_id] = fn
        return fn

    return decorator


@dataclass(frozen=True)
class ModelCapabilities:
    context_window: int | None
    supports_embeddings: bool
    supports_usage: bool
    supports_streaming: bool
    json_reliability: ReliabilityLevel
    state_block_reliability: ReliabilityLevel
    reasoning_leakage_risk: LeakageRiskLevel
    recommended_max_concurrency: int


@dataclass(frozen=True)
class ModelProfile:
    profile_id: str
    label: str
    provider_type: ProviderType
    base_url: str | None
    model_id: str
    api_key_env: str | None
    pricing_key: str
    capabilities: ModelCapabilities
    is_builtin: bool = True

    @property
    def context_window(self) -> int | None:
        return self.capabilities.context_window

    @property
    def supports_embeddings(self) -> bool:
        return self.capabilities.supports_embeddings

    @property
    def supports_usage(self) -> bool:
        return self.capabilities.supports_usage


@dataclass(frozen=True)
class RunProfileResolution:
    """Profiles attached to a queued simulation run."""

    requested_profile_id: str | None
    llm_provider: str
    hybrid_mode: bool
    primary_profile: ModelProfile
    local_profile: ModelProfile
    frontier_profile: ModelProfile


def capabilities_dict(cap: ModelCapabilities) -> dict[str, Any]:
    """Public capability metadata (no secrets)."""
    return {
        "context_window": cap.context_window,
        "supports_embeddings": cap.supports_embeddings,
        "supports_usage": cap.supports_usage,
        "supports_streaming": cap.supports_streaming,
        "json_reliability": cap.json_reliability,
        "state_block_reliability": cap.state_block_reliability,
        "reasoning_leakage_risk": cap.reasoning_leakage_risk,
        "recommended_max_concurrency": cap.recommended_max_concurrency,
    }


def resolve_run_llm_provider(
    *,
    request_llm_provider: str | None,
    model_profile_id: str | None,
    settings: Settings,
) -> str:
    """
    Effective ``llm_provider`` for a queued run.

    Explicit request value wins. Otherwise infer from built-in ``model_profile_id``
    (never ``hybrid``). Fall back to server settings.
    """
    if request_llm_provider is not None:
        return request_llm_provider.strip().lower()
    profile_id = (model_profile_id or "").strip()
    if profile_id:
        profile = get_builtin_profile(profile_id, settings)
        if profile is not None:
            if profile.provider_type == "openai_compatible":
                return "lmstudio"
            if profile.provider_type == "anthropic":
                return "anthropic"
    return (settings.llm_provider or "lmstudio").strip().lower()


def resolve_api_key_from_env(api_key_env: str | None) -> str:
    """Read API key from named environment variable (never log or snapshot the value)."""
    name = (api_key_env or "").strip()
    if not name:
        return ""
    return (os.environ.get(name) or "").strip()


def run_openai_compatible_api_key(resolution: RunProfileResolution) -> str:
    """Bearer token for the active OpenAI-compatible leg (local or commercial profile)."""
    return resolve_api_key_from_env(resolution.local_profile.api_key_env)


@register_builtin_profile(LOCAL_LMSTUDIO_DEFAULT_ID)
def local_lmstudio_default(settings: Settings) -> ModelProfile:
    return ModelProfile(
        profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
        label="Local LM Studio",
        provider_type="openai_compatible",
        base_url=settings.lmstudio_base_url,
        model_id=settings.lmstudio_model,
        api_key_env=None,
        pricing_key="lmstudio",
        is_builtin=True,
        capabilities=ModelCapabilities(
            context_window=None,
            supports_embeddings=True,
            supports_usage=True,
            supports_streaming=True,
            json_reliability="medium",
            state_block_reliability="medium",
            reasoning_leakage_risk="high",
            recommended_max_concurrency=4,
        ),
    )


def _commercial_openai_capabilities(
    *,
    context_window: int | None = 128_000,
    json_reliability: ReliabilityLevel = "high",
    state_block_reliability: ReliabilityLevel = "high",
    reasoning_leakage_risk: LeakageRiskLevel = "low",
    recommended_max_concurrency: int = 8,
) -> ModelCapabilities:
    return ModelCapabilities(
        context_window=context_window,
        supports_embeddings=False,
        supports_usage=True,
        supports_streaming=True,
        json_reliability=json_reliability,
        state_block_reliability=state_block_reliability,
        reasoning_leakage_risk=reasoning_leakage_risk,
        recommended_max_concurrency=recommended_max_concurrency,
    )


@register_builtin_profile(OPENAI_DEFAULT_ID)
def openai_default(settings: Settings) -> ModelProfile:
    return ModelProfile(
        profile_id=OPENAI_DEFAULT_ID,
        label="OpenAI",
        provider_type="openai_compatible",
        base_url=settings.openai_base_url,
        model_id=settings.openai_model,
        api_key_env=settings.openai_api_key_env,
        pricing_key="openai",
        is_builtin=True,
        capabilities=_commercial_openai_capabilities(),
    )


@register_builtin_profile(OPENROUTER_DEFAULT_ID)
def openrouter_default(settings: Settings) -> ModelProfile:
    return ModelProfile(
        profile_id=OPENROUTER_DEFAULT_ID,
        label="OpenRouter",
        provider_type="openai_compatible",
        base_url=settings.openrouter_base_url,
        model_id=settings.openrouter_model,
        api_key_env=settings.openrouter_api_key_env,
        pricing_key="openrouter",
        is_builtin=True,
        capabilities=_commercial_openai_capabilities(
            json_reliability="medium",
            state_block_reliability="medium",
        ),
    )


@register_builtin_profile(ANTHROPIC_DEFAULT_ID)
def anthropic_default(settings: Settings) -> ModelProfile:
    return ModelProfile(
        profile_id=ANTHROPIC_DEFAULT_ID,
        label="Anthropic default",
        provider_type="anthropic",
        base_url=None,
        model_id=settings.anthropic_model,
        api_key_env="ANTHROPIC_API_KEY",
        pricing_key="anthropic",
        is_builtin=True,
        capabilities=ModelCapabilities(
            context_window=200_000,
            supports_embeddings=False,
            supports_usage=True,
            supports_streaming=True,
            json_reliability="high",
            state_block_reliability="high",
            reasoning_leakage_risk="low",
            recommended_max_concurrency=8,
        ),
    )


# Derive built-in id set from registry (iter-36).
BUILTIN_PROFILE_IDS = frozenset(_BUILTIN_PROFILE_FACTORIES.keys())


def list_builtin_profiles(settings: Settings) -> list[ModelProfile]:
    """All registered built-in profiles for the current settings."""
    return [factory(settings) for factory in _BUILTIN_PROFILE_FACTORIES.values()]


def profile_capability_dict(profile: ModelProfile, *, is_default: bool) -> dict[str, Any]:
    """Public capability row for GET /capabilities (Senna iter-32, extended iter-36)."""
    label = profile.label
    if profile.profile_id == LOCAL_LMSTUDIO_DEFAULT_ID:
        label = "Local model"
    elif profile.profile_id == ANTHROPIC_DEFAULT_ID:
        label = "Claude"
    elif profile.profile_id == OPENAI_DEFAULT_ID:
        label = "OpenAI"
    elif profile.profile_id == OPENROUTER_DEFAULT_ID:
        label = "OpenRouter"
    return {
        "profile_id": profile.profile_id,
        "label": label,
        "provider_type": profile.provider_type,
        "model_id": profile.model_id,
        "is_default": is_default,
        "is_builtin": profile.is_builtin,
        "description": PROFILE_UI_DESCRIPTIONS.get(profile.profile_id, profile.label),
        "supports_usage": profile.supports_usage,
        "supports_embeddings": profile.supports_embeddings,
        "capabilities": capabilities_dict(profile.capabilities),
    }


def build_model_profiles_capabilities(settings: Settings) -> dict[str, Any]:
    """``model_profiles`` block and hybrid routing hint for capabilities."""
    profiles = list_builtin_profiles(settings)
    default_provider = (settings.llm_provider or "lmstudio").strip().lower()
    return {
        "profiles": [
            profile_capability_dict(
                p,
                is_default=(
                    p.profile_id == LOCAL_LMSTUDIO_DEFAULT_ID
                    and default_provider in ("lmstudio", "hybrid")
                )
                or (
                    p.profile_id == ANTHROPIC_DEFAULT_ID
                    and default_provider == "anthropic"
                ),
            )
            for p in profiles
        ],
        "hybrid_routing": {
            "label": HYBRID_ROUTING_LABEL,
            "description": HYBRID_ROUTING_DESCRIPTION,
            "llm_provider": "hybrid",
            "routing_policy": "hybrid_first_turn",
            "is_default": default_provider == "hybrid",
        },
    }


def get_builtin_profile(profile_id: str, settings: Settings) -> ModelProfile | None:
    pid = (profile_id or "").strip()
    factory = _BUILTIN_PROFILE_FACTORIES.get(pid)
    if factory is None:
        return None
    return factory(settings)


def resolve_run_profiles(
    *,
    model_profile_id: str | None,
    llm_provider: str,
    settings: Settings,
) -> RunProfileResolution:
    """
    Resolve built-in profiles for a run.

    - Explicit ``model_profile_id`` selects that built-in profile as primary.
    - No profile id: ``lmstudio`` → local default; ``anthropic`` → frontier default;
      ``hybrid`` → both (per-turn routing unchanged until iter-33).
    """
    mode = (llm_provider or "lmstudio").strip().lower()
    hybrid_mode = mode == "hybrid"
    local_p = local_lmstudio_default(settings)
    frontier_p = anthropic_default(settings)

    requested = (model_profile_id or "").strip() or None
    if requested:
        explicit = get_builtin_profile(requested, settings)
        if explicit is None:
            raise ValueError(
                f"Unknown model_profile_id {requested!r}; "
                f"expected one of: {sorted(BUILTIN_PROFILE_IDS)}"
            )
        return RunProfileResolution(
            requested_profile_id=requested,
            llm_provider=mode,
            hybrid_mode=hybrid_mode,
            primary_profile=explicit,
            local_profile=explicit if explicit.provider_type == "openai_compatible" else local_p,
            frontier_profile=explicit if explicit.provider_type == "anthropic" else frontier_p,
        )

    if mode == "anthropic":
        primary = frontier_p
    else:
        primary = local_p

    return RunProfileResolution(
        requested_profile_id=None,
        llm_provider=mode,
        hybrid_mode=hybrid_mode,
        primary_profile=primary,
        local_profile=local_p,
        frontier_profile=frontier_p,
    )


def profile_snapshot_dict(profile: ModelProfile) -> dict[str, Any]:
    """Reproducibility metadata for ``config_snapshot``."""
    return {
        "profile_id": profile.profile_id,
        "label": profile.label,
        "provider_type": profile.provider_type,
        "model_id": profile.model_id,
        "base_url": profile.base_url,
        "is_builtin": profile.is_builtin,
        "context_window": profile.context_window,
        "supports_embeddings": profile.supports_embeddings,
        "supports_usage": profile.supports_usage,
        "pricing_key": profile.pricing_key,
        "api_key_env": profile.api_key_env,
        "capabilities": capabilities_dict(profile.capabilities),
    }


def routing_policy_config_snapshot(resolution: RunProfileResolution) -> dict[str, Any]:
    """Routing policy + resolved profile ids for ``config_snapshot`` (iter-33)."""
    from mirofish_backend.llm.routing_policies import (
        LEGACY_HYBRID_ROUTING_POLICY,
        llm_provider_to_routing_policy,
    )

    policy = llm_provider_to_routing_policy(resolution.llm_provider)
    out: dict[str, Any] = {
        "routing_policy": policy,
        "routing_profile_local_id": resolution.local_profile.profile_id,
        "routing_profile_frontier_id": resolution.frontier_profile.profile_id,
    }
    if policy == "hybrid_first_turn":
        out["hybrid_routing_policy"] = LEGACY_HYBRID_ROUTING_POLICY
    else:
        out["hybrid_routing_policy"] = None
    return out


def model_profile_config_snapshot(resolution: RunProfileResolution) -> dict[str, Any]:
    """``config_snapshot`` keys for model profile provenance."""
    out: dict[str, Any] = {
        "model_profile_id": resolution.requested_profile_id,
        "model_profile_resolved_id": resolution.primary_profile.profile_id,
    }
    if resolution.hybrid_mode and resolution.requested_profile_id is None:
        out["model_profile"] = None
        out["model_profile_local"] = profile_snapshot_dict(resolution.local_profile)
        out["model_profile_frontier"] = profile_snapshot_dict(resolution.frontier_profile)
    else:
        out["model_profile"] = profile_snapshot_dict(resolution.primary_profile)
        if resolution.hybrid_mode:
            out["model_profile_local"] = profile_snapshot_dict(resolution.local_profile)
            out["model_profile_frontier"] = profile_snapshot_dict(resolution.frontier_profile)
    return out


def run_llm_credentials(
    resolution: RunProfileResolution,
    settings: Settings,
) -> tuple[str, str, str]:
    """
    Return ``(lmstudio_model, lmstudio_base_url, anthropic_model)`` for orchestration.

    When an explicit profile is set, its model/base URL override the matching leg.
    Hybrid without explicit profile uses built-in local + frontier defaults from settings.
    """
    lm_model = settings.lmstudio_model
    lm_url = settings.lmstudio_base_url
    ant_model = settings.anthropic_model

    if resolution.requested_profile_id:
        p = resolution.primary_profile
        if p.provider_type == "openai_compatible":
            lm_model = p.model_id
            if p.base_url:
                lm_url = p.base_url
        else:
            ant_model = p.model_id
        return lm_model, lm_url, ant_model

    if resolution.hybrid_mode:
        lp = resolution.local_profile
        fp = resolution.frontier_profile
        lm_model = lp.model_id
        if lp.base_url:
            lm_url = lp.base_url
        ant_model = fp.model_id
        return lm_model, lm_url, ant_model

    if resolution.llm_provider == "anthropic":
        ant_model = resolution.frontier_profile.model_id
    else:
        lp = resolution.local_profile
        lm_model = lp.model_id
        if lp.base_url:
            lm_url = lp.base_url

    return lm_model, lm_url, ant_model
