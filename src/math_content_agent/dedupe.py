"""History loading and duplicate-penalty helpers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .models import AppSettings, CandidateTopic


@dataclass(frozen=True)
class PostHistoryEntry:
    """Minimal historical record used for duplicate avoidance."""

    date: date
    topic: str
    entity: str
    theme: str
    status: str


def load_post_history(history_path: Path) -> list[PostHistoryEntry]:
    """Load post history rows from CSV, ignoring incomplete rows safely."""

    if not history_path.exists():
        return []

    entries: list[PostHistoryEntry] = []
    with history_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw_date = (row.get("date") or "").strip()
            if not raw_date:
                continue
            entries.append(
                PostHistoryEntry(
                    date=date.fromisoformat(raw_date),
                    topic=(row.get("topic") or "").strip(),
                    entity=(row.get("entity") or "").strip(),
                    theme=(row.get("theme") or "").strip(),
                    status=(row.get("status") or "").strip(),
                )
            )
    return entries


def calculate_duplicate_penalty(
    candidate: CandidateTopic,
    history: list[PostHistoryEntry],
    run_date: date,
    settings: AppSettings,
) -> tuple[float, list[str]]:
    """Compute recent-history penalties and explanation notes."""

    recent_cutoff = run_date - timedelta(days=settings.recent_history_window_days)
    recent_entries = [entry for entry in history if entry.date >= recent_cutoff]

    penalty = 0.0
    notes: list[str] = []

    matching_topics = [entry for entry in recent_entries if entry.topic.casefold() == candidate.title.casefold()]
    if matching_topics:
        latest = max(matching_topics, key=lambda entry: entry.date)
        penalty += settings.duplicate_topic_penalty
        notes.append(
            f"Potential repeat: the same topic title appeared on {latest.date.isoformat()} ({latest.status or 'UNKNOWN'})."
        )

    matching_entities = [
        entry
        for entry in recent_entries
        if candidate.entity and entry.entity and entry.entity.casefold() == candidate.entity.casefold()
    ]
    if matching_entities:
        latest = max(matching_entities, key=lambda entry: entry.date)
        penalty += settings.duplicate_entity_penalty
        notes.append(
            f"Potential repeat: the same mathematician or concept appeared on {latest.date.isoformat()} ({latest.status or 'UNKNOWN'})."
        )

    matching_themes = [entry for entry in recent_entries if entry.theme.casefold() == candidate.theme_slug.casefold()]
    if matching_themes:
        latest = max(matching_themes, key=lambda entry: entry.date)
        penalty += settings.duplicate_theme_penalty
        notes.append(
            f"Theme repeat note: this weekday theme was also used on {latest.date.isoformat()} ({latest.status or 'UNKNOWN'})."
        )

    return penalty, notes
