"""Tests for news-first selection and fallback logic."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, date, datetime

from math_content_agent.config import ensure_runtime_dirs, load_settings, load_trusted_sources
from math_content_agent.news import build_daily_selection_plan, select_news_candidates, write_news_debug
from math_content_agent.models import NewsCandidate


class StaticNewsProvider:
    """Simple in-memory provider used by tests."""

    def __init__(self, items: list[NewsCandidate]) -> None:
        self.items = items

    def fetch(self, run_date: date) -> list[NewsCandidate]:
        return self.items


class NewsSelectionTests(unittest.TestCase):
    def test_valid_news_is_selected(self) -> None:
        settings = load_settings(env={"NEWS_MIN_SOURCES": "1"})
        selection = select_news_candidates(
            run_date=date(2026, 4, 20),
            settings=settings,
            source_policy=load_trusted_sources(),
            provider=StaticNewsProvider(
                [
                    NewsCandidate(
                        title="New telescope data sharpens orbital model",
                        slug="telescope-orbital-model",
                        url="https://www.siam.org/news/orbital-model",
                        source_name="SIAM",
                        published_at="2026-04-18",
                        topic_domain="astronomy",
                        summary="Researchers published a clearer orbital model based on fresh observations.",
                        math_relevance="The story depends on mathematical modeling and numerical analysis.",
                        source_count=2,
                        major_claims_clear=True,
                        is_speculative=False,
                    )
                ]
            ),
            checked_at=datetime(2026, 4, 20, 2, 0, tzinfo=UTC),
        )

        self.assertEqual(selection.mode, "NEWS_MODE")
        self.assertIsNotNone(selection.selected_candidate)
        self.assertEqual(selection.selected_candidate.title, "New telescope data sharpens orbital model")

    def test_weak_news_falls_back(self) -> None:
        settings = load_settings(env={})
        plan = build_daily_selection_plan(
            run_date=date(2026, 4, 20),
            weekday_name="Monday",
            theme_slug="history",
            theme_label="Mathematician birthdays and history",
            settings=settings,
            source_policy=load_trusted_sources(),
            provider=StaticNewsProvider(
                [
                    NewsCandidate(
                        title="Speculative physics rumor spreads online",
                        slug="speculative-physics-rumor",
                        url="https://unknown.example/speculative-rumor",
                        source_name="Unknown",
                        published_at="2026-04-19",
                        topic_domain="science",
                        summary="A rumor claims a major breakthrough.",
                        math_relevance="",
                        source_count=1,
                        major_claims_clear=False,
                        is_speculative=True,
                    )
                ]
            ),
            checked_at=datetime(2026, 4, 20, 2, 0, tzinfo=UTC),
        )

        self.assertEqual(plan.mode, "STANDARD_MATH_MODE")
        self.assertIsNotNone(plan.planner_run)
        self.assertIsNone(plan.news_selection.selected_candidate)

    def test_news_debug_output_is_written(self) -> None:
        settings = load_settings(env={"NEWS_MIN_SOURCES": "1"})
        ensure_runtime_dirs(settings)
        selection = select_news_candidates(
            run_date=date(2026, 4, 20),
            settings=settings,
            source_policy=load_trusted_sources(),
            provider=StaticNewsProvider(
                [
                    NewsCandidate(
                        title="Math outreach study reports clearer classroom gains",
                        slug="math-outreach-classroom-gains",
                        url="https://www.ams.org/news/classroom-gains",
                        source_name="AMS",
                        published_at="2026-04-19",
                        topic_domain="mathematics",
                        summary="An outreach report summarized measurable learning gains.",
                        math_relevance="The report is directly about mathematics education and evidence-based reasoning.",
                        source_count=2,
                        major_claims_clear=True,
                        is_speculative=False,
                    )
                ]
            ),
            checked_at=datetime(2026, 4, 20, 2, 0, tzinfo=UTC),
        )

        path = write_news_debug(selection, settings.candidate_cache_dir)
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["mode"], "NEWS_MODE")
        self.assertEqual(payload["selected_candidate"]["slug"], "math-outreach-classroom-gains")


if __name__ == "__main__":
    unittest.main()
