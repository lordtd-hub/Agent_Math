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

    if any(entry.topic.casefold() == candidate.title.casefold() for entry in recent_entries):
        penalty += settings.duplicate_topic_penalty
        notes.append("Recent history contains the same topic title, so the score is reduced.")

    if candidate.entity and any(
        entry.entity.casefold() == candidate.entity.casefold() for entry in recent_entries if entry.entity
    ):
        penalty += settings.duplicate_entity_penalty
        notes.append("Recent history contains the same mathematician or concept, so the score is reduced.")

    if any(entry.theme.casefold() == candidate.theme_slug.casefold() for entry in recent_entries):
        penalty += settings.duplicate_theme_penalty
        notes.append("This weekday theme appeared recently, so a small repeat penalty was applied.")

    return penalty, notes
