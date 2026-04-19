"""Tests for config loading and environment overrides."""

from __future__ import annotations

import unittest
from pathlib import Path

from math_content_agent.config import ensure_runtime_dirs, load_settings, project_root


class ConfigTests(unittest.TestCase):
    def test_load_settings_uses_repo_defaults(self) -> None:
        settings = load_settings(env={})

        self.assertEqual(settings.timezone, "Asia/Bangkok")
        self.assertEqual(settings.output_language, "th")
        self.assertEqual(settings.post_mode, "draft_only")
        self.assertTrue(settings.facebook_dry_run)
        self.assertEqual(settings.confidence_threshold, 0.85)
        self.assertTrue(settings.news_enabled)
        self.assertEqual(settings.news_max_age_days, 7)
        self.assertEqual(settings.news_min_sources, 1)
        self.assertTrue(settings.news_require_multi_source_for_major_claims)
        self.assertEqual(settings.planner_candidate_target, 5)
        self.assertEqual(settings.daily_review_dir, project_root() / "outputs" / "daily_reviews")
        self.assertEqual(settings.approval_dir, project_root() / "outputs" / "approvals")
        self.assertEqual(settings.raw_evidence_dir, project_root() / "outputs" / "raw_evidence")

    def test_environment_overrides_apply(self) -> None:
        settings = load_settings(
            env={
                "TIMEZONE": "UTC",
                "OUTPUT_LANGUAGE": "th",
                "POST_MODE": "approve_then_schedule",
                "FACEBOOK_DRY_RUN": "false",
                "CONFIDENCE_THRESHOLD": "0.91",
                "WEEKDAY_SCHEDULE_ENABLED": "false",
                "NEWS_ENABLED": "false",
                "NEWS_MAX_AGE_DAYS": "5",
                "NEWS_MIN_SOURCES": "2",
                "NEWS_REQUIRE_MULTI_SOURCE_FOR_MAJOR_CLAIMS": "false",
            }
        )

        self.assertEqual(settings.timezone, "UTC")
        self.assertEqual(settings.output_language, "th")
        self.assertEqual(settings.post_mode, "approve_then_schedule")
        self.assertFalse(settings.facebook_dry_run)
        self.assertEqual(settings.confidence_threshold, 0.91)
        self.assertFalse(settings.weekday_schedule_enabled)
        self.assertFalse(settings.news_enabled)
        self.assertEqual(settings.news_max_age_days, 5)
        self.assertEqual(settings.news_min_sources, 2)
        self.assertFalse(settings.news_require_multi_source_for_major_claims)

    def test_runtime_dirs_exist_after_ensure(self) -> None:
        settings = load_settings(env={})
        ensure_runtime_dirs(settings)

        for directory in (
            settings.daily_review_dir,
            settings.verification_json_dir,
            settings.approval_dir,
            settings.logs_dir,
        ):
            self.assertTrue(Path(directory).exists())


if __name__ == "__main__":
    unittest.main()
