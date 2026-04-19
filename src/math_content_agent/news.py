"""News-first detection and selection with safe fallback rules."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

from .models import AppSettings, DailySelectionPlan, NewsCandidate, NewsSelectionResult, PlannerRun
from .planner import plan_topics
from .retriever import is_allowed_source

ALLOWED_NEWS_DOMAINS = {"mathematics", "science", "astronomy"}


class NewsProvider(Protocol):
    """Provider interface for recent news discovery."""

    def fetch(self, run_date: date) -> list[NewsCandidate]:
        """Return recent news candidates for the requested date."""


class EmptyNewsProvider:
    """Default provider used until a real news integration is added."""

    def fetch(self, run_date: date) -> list[NewsCandidate]:
        return []


def _days_old(run_date: date, published_at: str) -> int | None:
    """Return the age of a news item in days when the timestamp is parseable."""

    try:
        published_date = date.fromisoformat(published_at[:10])
    except ValueError:
        return None
    return (run_date - published_date).days


def select_news_candidates(
    run_date: date,
    settings: AppSettings,
    source_policy: dict[str, object],
    provider: NewsProvider | None = None,
    checked_at: datetime | None = None,
) -> NewsSelectionResult:
    """Select valid news items according to the updated spec."""

    current_time = checked_at or datetime.now(UTC)
    if not settings.news_enabled:
        return NewsSelectionResult(
            checked_at=current_time,
            mode="STANDARD_MATH_MODE",
            reasons=["News mode is disabled in settings, so the pipeline will use standard math topic mode."],
            candidates_considered=[],
            valid_candidates=[],
            selected_candidate=None,
        )

    raw_candidates = (provider or EmptyNewsProvider()).fetch(run_date)
    valid_candidates: list[NewsCandidate] = []
    reasons: list[str] = []

    for candidate in raw_candidates:
        if candidate.topic_domain not in ALLOWED_NEWS_DOMAINS:
            reasons.append(f"Rejected '{candidate.title}' because its domain was outside math/science/astronomy.")
            continue
        if not is_allowed_source(candidate.url, source_policy):
            reasons.append(f"Rejected '{candidate.title}' because its source was not on the allowlist.")
            continue

        age_in_days = _days_old(run_date, candidate.published_at)
        if age_in_days is None:
            reasons.append(f"Rejected '{candidate.title}' because its publication date could not be parsed.")
            continue
        if age_in_days < 0 or age_in_days > settings.news_max_age_days:
            reasons.append(
                f"Rejected '{candidate.title}' because it was {age_in_days} days old, outside the configured news window."
            )
            continue
        if candidate.source_count < settings.news_min_sources:
            reasons.append(f"Rejected '{candidate.title}' because it did not meet the minimum source count.")
            continue
        if settings.news_require_multi_source_for_major_claims and candidate.source_count < 2:
            reasons.append(f"Rejected '{candidate.title}' because major claims were not backed by multiple sources.")
            continue
        if not candidate.major_claims_clear:
            reasons.append(f"Rejected '{candidate.title}' because its key claims were not clear enough for academic use.")
            continue
        if candidate.is_speculative:
            reasons.append(f"Rejected '{candidate.title}' because it was marked speculative.")
            continue
        if not candidate.math_relevance.strip():
            reasons.append(f"Rejected '{candidate.title}' because it lacked an explicit math/science relevance note.")
            continue

        valid_candidates.append(candidate)

    selected = valid_candidates[0] if valid_candidates else None
    mode = "NEWS_MODE" if selected else "STANDARD_MATH_MODE"
    if selected:
        reasons.append(f"Selected '{selected.title}' for NEWS_MODE because it passed source, recency, and clarity checks.")
    else:
        reasons.append("No news item passed the strict rules, so the pipeline will fall back to standard math topic mode.")

    return NewsSelectionResult(
        checked_at=current_time,
        mode=mode,
        reasons=reasons,
        candidates_considered=raw_candidates,
        valid_candidates=valid_candidates,
        selected_candidate=selected,
    )


def build_daily_selection_plan(
    run_date: date,
    weekday_name: str,
    theme_slug: str,
    theme_label: str,
    settings: AppSettings,
    source_policy: dict[str, object],
    provider: NewsProvider | None = None,
    checked_at: datetime | None = None,
) -> DailySelectionPlan:
    """Build the daily mode-selection plan before retrieval/verification."""

    news_selection = select_news_candidates(
        run_date=run_date,
        settings=settings,
        source_policy=source_policy,
        provider=provider,
        checked_at=checked_at,
    )
    if news_selection.selected_candidate is not None:
        return DailySelectionPlan(
            mode="NEWS_MODE",
            run_date=run_date,
            weekday_name=weekday_name,
            output_language=settings.output_language,
            reasons=news_selection.reasons,
            news_selection=news_selection,
            planner_run=None,
        )

    planner_run = plan_topics(
        run_date=run_date,
        weekday_name=weekday_name,
        theme_slug=theme_slug,
        theme_label=theme_label,
        settings=settings,
    )
    return DailySelectionPlan(
        mode="STANDARD_MATH_MODE",
        run_date=run_date,
        weekday_name=weekday_name,
        output_language=settings.output_language,
        reasons=news_selection.reasons,
        news_selection=news_selection,
        planner_run=planner_run,
    )


def write_news_debug(selection: NewsSelectionResult, output_dir: Path) -> Path:
    """Store news candidate evaluation details for auditing."""

    payload = {
        "checked_at": selection.checked_at.replace(microsecond=0).isoformat(),
        "mode": selection.mode,
        "reasons": selection.reasons,
        "selected_candidate": asdict(selection.selected_candidate) if selection.selected_candidate else None,
        "valid_candidates": [asdict(candidate) for candidate in selection.valid_candidates],
        "candidates_considered": [asdict(candidate) for candidate in selection.candidates_considered],
    }
    path = output_dir / f"{selection.checked_at.date().isoformat()}_news_candidates.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
