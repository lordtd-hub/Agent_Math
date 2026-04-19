"""Tests for review package generation."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, date, datetime

from math_content_agent.config import ensure_runtime_dirs, load_settings
from math_content_agent.models import DraftPost, EvidenceBundle, EvidenceItem, VerificationResult
from math_content_agent.package_builder import build_review_package, write_review_package


class PackageBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = EvidenceBundle(
            content_mode="STANDARD_MATH_MODE",
            candidate_slug="gauss-number-theory-turning-point",
            candidate_title="Gauss กับจุดเปลี่ยนของทฤษฎีจำนวน",
            generated_at=datetime(2026, 4, 20, 2, 0, tzinfo=UTC),
            allowed_items=[
                EvidenceItem(
                    title="Gauss biography",
                    source="AMS",
                    url="https://www.ams.org/gauss",
                    excerpt="Historical source describing Gauss and number theory.",
                    source_type="reference",
                    source_tier="tier_1",
                    published_at="2024-01-01",
                    content_mode="STANDARD_MATH_MODE",
                    candidate_slug="gauss-number-theory-turning-point",
                    candidate_title="Gauss กับจุดเปลี่ยนของทฤษฎีจำนวน",
                    confidence_notes=[],
                ),
                EvidenceItem(
                    title="Gauss archive",
                    source="Mactutor",
                    url="https://mathshistory.st-andrews.ac.uk/Gauss/",
                    excerpt="Second historical source describing the same theme.",
                    source_type="reference",
                    source_tier="tier_2",
                    published_at="2024-01-02",
                    content_mode="STANDARD_MATH_MODE",
                    candidate_slug="gauss-number-theory-turning-point",
                    candidate_title="Gauss กับจุดเปลี่ยนของทฤษฎีจำนวน",
                    confidence_notes=[],
                ),
            ],
            rejected_urls=[],
        )
        self.draft = DraftPost(
            content_mode="STANDARD_MATH_MODE",
            topic_title="Gauss กับจุดเปลี่ยนของทฤษฎีจำนวน",
            why_relevant="วันที่ 2026-04-20 ตรงกับธีมวันจันทร์ของเพจ",
            body="วันนี้ภาควิชาคณิตศาสตร์ชวนมองเรื่อง Gauss กับจุดเปลี่ยนของทฤษฎีจำนวน",
            fact_summary=["AMS: Historical source describing Gauss and number theory."],
            hashtags=["#คณิตศาสตร์"],
        )
        self.good_verification = VerificationResult(
            content_mode="STANDARD_MATH_MODE",
            publishable=True,
            confidence=0.90,
            topic_title=self.draft.topic_title,
            date_link_type="weekday_theme",
            fact_checks=[],
            conflicts=[],
            verification_notes=["Standard topic verification passed."],
            required_human_review=True,
            reason="Ready for review.",
        )
        self.bad_verification = VerificationResult(
            content_mode="STANDARD_MATH_MODE",
            publishable=False,
            confidence=0.52,
            topic_title=self.draft.topic_title,
            date_link_type="weekday_theme",
            fact_checks=[],
            conflicts=["Conflicting evidence found."],
            verification_notes=["Low confidence."],
            required_human_review=True,
            reason="Blocked.",
        )

    def test_build_review_package_uses_pending_review_for_publishable(self) -> None:
        review = build_review_package(date(2026, 4, 20), self.draft, self.good_verification, self.bundle)

        self.assertEqual(review.status, "PENDING_REVIEW")
        self.assertIn("#คณิตศาสตร์", review.thai_draft)
        self.assertEqual(len(review.short_references), 2)

    def test_build_review_package_blocks_low_confidence(self) -> None:
        review = build_review_package(date(2026, 4, 20), self.draft, self.bad_verification, self.bundle)

        self.assertEqual(review.status, "BLOCKED_LOW_CONFIDENCE")
        self.assertTrue(review.verification_notes)

    def test_write_review_package_outputs_markdown_and_json(self) -> None:
        settings = load_settings(env={})
        ensure_runtime_dirs(settings)
        review = build_review_package(date(2026, 4, 20), self.draft, self.good_verification, self.bundle)

        markdown_path, json_path = write_review_package(
            review,
            settings.daily_review_dir,
            settings.verification_json_dir,
        )
        markdown_text = markdown_path.read_text(encoding="utf-8")
        payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertIn("## Draft Facebook Post", markdown_text)
        self.assertEqual(payload["status"], "PENDING_REVIEW")
        self.assertEqual(payload["proposed_topic"], self.draft.topic_title)


if __name__ == "__main__":
    unittest.main()
