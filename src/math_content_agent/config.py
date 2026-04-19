"""Configuration loading helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import AppSettings


def project_root() -> Path:
    """Return the repository root directory."""

    return Path(__file__).resolve().parents[2]


def default_config_dir() -> Path:
    """Return the default config directory."""

    return project_root() / "config"


def _read_json_subset_yaml(path: Path) -> dict[str, Any]:
    """Read a `.yaml` file that currently uses the JSON subset of YAML."""

    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_env_value(raw_value: str, expected_type: type[Any]) -> Any:
    """Convert environment strings into the target scalar type."""

    if expected_type is bool:
        return raw_value.strip().lower() in {"1", "true", "yes", "on"}
    if expected_type is float:
        return float(raw_value)
    if expected_type is int:
        return int(raw_value)
    return raw_value


def _apply_environment_overrides(data: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    """Overlay selected settings from environment variables."""

    overrides = {
        "timezone": "TIMEZONE",
        "output_language": "OUTPUT_LANGUAGE",
        "post_mode": "POST_MODE",
        "facebook_dry_run": "FACEBOOK_DRY_RUN",
        "confidence_threshold": "CONFIDENCE_THRESHOLD",
        "weekday_schedule_enabled": "WEEKDAY_SCHEDULE_ENABLED",
        "news_enabled": "NEWS_ENABLED",
        "news_max_age_days": "NEWS_MAX_AGE_DAYS",
        "news_min_sources": "NEWS_MIN_SOURCES",
        "news_require_multi_source_for_major_claims": "NEWS_REQUIRE_MULTI_SOURCE_FOR_MAJOR_CLAIMS",
    }

    result = dict(data)
    for field_name, env_name in overrides.items():
        if env_name in env:
            current_value = result.get(field_name)
            expected_type = type(current_value) if current_value is not None else str
            result[field_name] = _coerce_env_value(env[env_name], expected_type)
    return result


def load_settings(config_dir: Path | None = None, env: dict[str, str] | None = None) -> AppSettings:
    """Load core application settings."""

    resolved_config_dir = config_dir or default_config_dir()
    raw_data = _read_json_subset_yaml(resolved_config_dir / "settings.yaml")
    merged = _apply_environment_overrides(raw_data, env or dict(os.environ))

    root = project_root()
    return AppSettings(
        timezone=merged["timezone"],
        output_language=merged["output_language"],
        post_mode=merged["post_mode"],
        facebook_dry_run=bool(merged["facebook_dry_run"]),
        confidence_threshold=float(merged["confidence_threshold"]),
        weekday_schedule_enabled=bool(merged["weekday_schedule_enabled"]),
        news_enabled=bool(merged["news_enabled"]),
        news_max_age_days=int(merged["news_max_age_days"]),
        news_min_sources=int(merged["news_min_sources"]),
        news_require_multi_source_for_major_claims=bool(merged["news_require_multi_source_for_major_claims"]),
        daily_review_dir=root / merged["daily_review_dir"],
        verification_json_dir=root / merged["verification_json_dir"],
        approval_dir=root / merged["approval_dir"],
        raw_evidence_dir=root / merged["raw_evidence_dir"],
        logs_dir=root / merged["logs_dir"],
        planner_candidate_target=int(merged["planner_candidate_target"]),
        post_history_path=root / merged["post_history_path"],
        candidate_cache_dir=root / merged["candidate_cache_dir"],
        recent_history_window_days=int(merged["recent_history_window_days"]),
        duplicate_topic_penalty=float(merged["duplicate_topic_penalty"]),
        duplicate_entity_penalty=float(merged["duplicate_entity_penalty"]),
        duplicate_theme_penalty=float(merged["duplicate_theme_penalty"]),
    )


def load_weekday_themes(config_dir: Path | None = None) -> dict[str, dict[str, str]]:
    """Load weekday theme definitions."""

    resolved_config_dir = config_dir or default_config_dir()
    return _read_json_subset_yaml(resolved_config_dir / "weekday_themes.yaml")


def load_trusted_sources(config_dir: Path | None = None) -> dict[str, Any]:
    """Load trusted source policy configuration."""

    resolved_config_dir = config_dir or default_config_dir()
    return _read_json_subset_yaml(resolved_config_dir / "trusted_sources.yaml")


def ensure_runtime_dirs(settings: AppSettings) -> None:
    """Create runtime output directories if they do not already exist."""

    for directory in (
        settings.daily_review_dir,
        settings.verification_json_dir,
        settings.approval_dir,
        settings.raw_evidence_dir,
        settings.logs_dir,
        settings.candidate_cache_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
