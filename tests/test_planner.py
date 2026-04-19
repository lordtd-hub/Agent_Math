"""Tests for topic planning and duplicate penalties."""

from __future__ import annotations

import json
import unittest
from datetime import date, datetime

from math_content_agent.config import ensure_runtime_dirs, load_settings
from math_content_agent.planner import plan_topics, write_planner_debug
from math_content_agent.utils import get_timezone


class PlannerTests(unittest.TestCase):
    def test_planner_produces_multiple_candidates_with_reasons(self) -> None:
        settings = load_settings(env={})
        run = plan_topics(
            run_date=date(2026, 4, 20),
            weekday_name="Monday",
            theme_slug="history",
            theme_label="Mathematician birthdays and history",
            settings=settings,
        )

        self.assertEqual(run.output_language, "th")
        self.assertGreaterEqual(len(run.candidates), 3)
        self.assertLessEqual(len(run.candidates), settings.planner_candidate_target)
        self.assertTrue(all(candidate.reasons for candidate in run.candidates))
        self.assertEqual(run.selected_candidate, run.candidates[0])

    def test_recent_duplicate_topic_is_penalized(self) -> None:
        settings = load_settings(env={})
        run = plan_topics(
            run_date=date(2026, 4, 20),
            weekday_name="Monday",
            theme_slug="history",
            theme_label="Mathematician birthdays and history",
            settings=settings,
        )

        duplicate = next(candidate for candidate in run.candidates if candidate.entity == "Leonhard Euler")
        self.assertGreater(duplicate.duplicate_penalty, 0.0)
        self.assertLess(duplicate.final_score, duplicate.base_score)

    def test_planner_output_is_written_to_cache(self) -> None:
        settings = load_settings(env={})
        ensure_runtime_dirs(settings)
        run = plan_topics(
            run_date=date(2026, 4, 24),
            weekday_name="Friday",
            theme_slug="applications",
            theme_label="Mathematics in real life",
            settings=settings,
        )
        path = write_planner_debug(
            run,
            settings.candidate_cache_dir,
            datetime(2026, 4, 24, 9, 0, tzinfo=get_timezone("Asia/Bangkok")),
        )

        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["output_language"], "th")
        self.assertEqual(payload["theme_slug"], "applications")
        self.assertTrue(payload["candidates"])


if __name__ == "__main__":
    unittest.main()
