"""Shared runtime helpers for scheduler decisions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config import load_settings, load_weekday_themes
from .models import SchedulerDecision
from .utils import is_weekday, normalize_now, weekday_name


def evaluate_run_day(now: datetime | None = None, config_dir: Path | None = None) -> SchedulerDecision:
    """Evaluate whether the pipeline should continue for the current day."""

    settings = load_settings(config_dir=config_dir)
    current_time = normalize_now(now, settings.timezone)
    run_date = current_time.date()
    day_name = weekday_name(run_date)
    themes = load_weekday_themes(config_dir=config_dir)
    theme = themes.get(day_name)

    if not settings.weekday_schedule_enabled:
        return SchedulerDecision(
            should_run=False,
            run_date=run_date,
            weekday_name=day_name,
            evaluated_at=current_time,
            reason="Weekday scheduler is disabled in settings.",
            theme_slug=theme["slug"] if theme else None,
            theme_label=theme["label"] if theme else None,
        )

    if not is_weekday(run_date):
        return SchedulerDecision(
            should_run=False,
            run_date=run_date,
            weekday_name=day_name,
            evaluated_at=current_time,
            reason="Weekend detected. Scheduler exits cleanly without generating a draft.",
        )

    return SchedulerDecision(
        should_run=True,
        run_date=run_date,
        weekday_name=day_name,
        evaluated_at=current_time,
        reason="Weekday detected. Scheduler can continue into later pipeline phases.",
        theme_slug=theme["slug"] if theme else None,
        theme_label=theme["label"] if theme else None,
    )
