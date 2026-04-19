"""Tests for end-to-end orchestration."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, date, datetime

from math_content_agent.approval import load_approval
from math_content_agent.config import ensure_runtime_dirs, load_settings
from math_content_agent.models import NewsCandidate
from math_content_agent.orchestrator import generate_daily_review, publish_from_approval
from math_content_agent.package_builder import load_review_package
from math_content_agent.publisher_facebook import FacebookPublishTransport


class StaticNewsProviderForOrchestrator:
    """Simple provider used to force NEWS_MODE in tests."""

    def fetch(self, run_date: date) -> list[NewsCandidate]:
        return [
            NewsCandidate(
                title="New telescope data sharpens orbital model",
                slug="telescope-orbital-model",
                url="https://www.siam.org/news/orbital-model",
                source_name="SIAM",
                published_at="2026-04-18",
                topic_domain="astronomy",
                summary="นักวิจัยรายงานข้อมูลใหม่ที่ช่วยให้แบบจำลองวงโคจรแม่นยำขึ้น",
                math_relevance="ข่าวนี้อาศัยแบบจำลองเชิงคณิตศาสตร์และการวิเคราะห์เชิงตัวเลข",
                source_count=2,
                major_claims_clear=True,
                is_speculative=False,
            )
        ]


class FakeTransport(FacebookPublishTransport):
    """Transport used for publish orchestration tests."""

    def publish_post(
        self,
        *,
        page_id: str,
        access_token: str,
        message: str,
        scheduled_publish_at: datetime | None = None,
    ) -> dict[str, object]:
        return {"id": "fb_post_999"}


class OrchestratorTests(unittest.TestCase):
    def test_generate_daily_review_creates_artifacts(self) -> None:
        artifacts = generate_daily_review(now=datetime(2026, 4, 20, 9, 0, tzinfo=UTC))

        self.assertTrue(artifacts.should_run)
        self.assertIsNotNone(artifacts.review)
        self.assertTrue(artifacts.review_markdown_path.exists())
        self.assertTrue(artifacts.review_json_path.exists())
        self.assertTrue(artifacts.approval_template_path.exists())
        self.assertEqual(artifacts.review.status, "PENDING_REVIEW")

    def test_generate_daily_review_supports_news_mode(self) -> None:
        settings = load_settings(env={"NEWS_MIN_SOURCES": "1"})
        ensure_runtime_dirs(settings)
        artifacts = generate_daily_review(
            now=datetime(2026, 4, 20, 9, 0, tzinfo=UTC),
            news_provider=StaticNewsProviderForOrchestrator(),
        )

        self.assertTrue(artifacts.should_run)
        self.assertEqual(artifacts.mode, "NEWS_MODE")
        self.assertEqual(artifacts.review.content_mode, "NEWS_MODE")

    def test_generate_daily_review_skips_weekend(self) -> None:
        artifacts = generate_daily_review(now=datetime(2026, 4, 18, 9, 0, tzinfo=UTC))

        self.assertFalse(artifacts.should_run)
        self.assertIsNone(artifacts.review)

    def test_publish_from_approval_updates_review_and_log(self) -> None:
        settings = load_settings(env={"POST_MODE": "approve_then_post", "FACEBOOK_DRY_RUN": "true"})
        ensure_runtime_dirs(settings)
        generate_daily_review(now=datetime(2026, 4, 20, 9, 0, tzinfo=UTC))

        approval_path = settings.approval_dir / "2026-04-20_approval.json"
        approval_payload = json.loads(approval_path.read_text(encoding="utf-8"))
        approval_payload["status"] = "APPROVED"
        approval_payload["notes"] = "พร้อมโพสต์"
        approval_path.write_text(json.dumps(approval_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        artifacts = publish_from_approval(
            run_date=date(2026, 4, 20),
            post_mode="approve_then_post",
            dry_run=True,
            page_id="123",
            access_token="token",
            transport=FakeTransport(),
        )

        review = load_review_package(artifacts.review_json_path)
        approval = load_approval(artifacts.approval_path)
        self.assertEqual(approval.status, "APPROVED")
        self.assertEqual(artifacts.publish_result.status, "PUBLISHED")
        self.assertEqual(review.status, "PUBLISHED")
        self.assertTrue(artifacts.publish_log_path.exists())


if __name__ == "__main__":
    unittest.main()
