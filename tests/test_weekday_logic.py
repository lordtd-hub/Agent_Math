"""Tests for weekday detection and weekend skip behavior."""

from __future__ import annotations

import unittest
from datetime import datetime

from math_content_agent.scheduler import evaluate_run_day
from math_content_agent.utils import get_timezone, is_weekday


class WeekdayLogicTests(unittest.TestCase):
    def test_is_weekday_true_for_monday(self) -> None:
        self.assertTrue(is_weekday(datetime(2026, 4, 20).date()))

    def test_is_weekday_false_for_saturday(self) -> None:
        self.assertFalse(is_weekday(datetime(2026, 4, 18).date()))

    def test_scheduler_runs_on_weekday(self) -> None:
        bangkok = get_timezone("Asia/Bangkok")
        decision = evaluate_run_day(datetime(2026, 4, 20, 9, 0, tzinfo=bangkok))

        self.assertTrue(decision.should_run)
        self.assertEqual(decision.weekday_name, "Monday")
        self.assertEqual(decision.theme_slug, "history")

    def test_scheduler_skips_weekend_cleanly(self) -> None:
        bangkok = get_timezone("Asia/Bangkok")
        decision = evaluate_run_day(datetime(2026, 4, 18, 9, 0, tzinfo=bangkok))

        self.assertFalse(decision.should_run)
        self.assertEqual(decision.weekday_name, "Saturday")
        self.assertIn("Weekend detected", decision.reason)


if __name__ == "__main__":
    unittest.main()
