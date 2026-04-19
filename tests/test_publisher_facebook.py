"""Tests for the Facebook publishing workflow."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, date, datetime

from math_content_agent.config import ensure_runtime_dirs, load_settings
from math_content_agent.models import ApprovalGateDecision, ReviewPackage
from math_content_agent.publisher_facebook import publish_review_package, write_publish_log


class FakeFacebookTransport:
    """In-memory transport used by publisher tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def publish_post(
        self,
        *,
        page_id: str,
        access_token: str,
        message: str,
        scheduled_publish_at: datetime | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "page_id": page_id,
                "access_token": access_token,
                "message": message,
                "scheduled_publish_at": scheduled_publish_at.isoformat() if scheduled_publish_at else None,
            }
        )
        return {"id": "fb_post_123"}


class FailingFacebookTransport:
    """Transport that raises to test failure logging."""

    def publish_post(
        self,
        *,
        page_id: str,
        access_token: str,
        message: str,
        scheduled_publish_at: datetime | None = None,
    ) -> dict[str, object]:
        raise RuntimeError("Simulated Facebook API failure")


class PublisherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = ReviewPackage(
            run_date=date(2026, 4, 20),
            content_mode="STANDARD_MATH_MODE",
            proposed_topic="Gauss กับจุดเปลี่ยนของทฤษฎีจำนวน",
            date_relevance_type="weekday_theme",
            why_relevant="วันที่ 2026-04-20 ตรงกับวันจันทร์ และหัวข้อนี้ถูกเลือกเพราะเข้ากับธีมประจำวัน",
            thai_draft="ร่างโพสต์ภาษาไทย\n\n#คณิต(วิทย์)มรส. #MathSCISRU",
            fact_summary=["ข้อเท็จจริงที่ผ่านการตรวจสอบ"],
            short_references=["AMS - Gauss biography"],
            full_references=["AMS. Gauss biography. https://www.ams.org/gauss"],
            duplicate_notes=["Potential repeat: the same mathematician or concept appeared on 2026-04-10 (PUBLISHED)."],
            verification_notes=["พร้อมให้ผู้ดูแลตรวจ"],
            confidence=0.90,
            status="PENDING_REVIEW",
        )
        self.approved = ApprovalGateDecision(
            can_publish=True,
            final_status="APPROVED",
            reason="Explicit human approval is present.",
            reviewer="admin",
            notes="พร้อมโพสต์",
        )
        self.blocked = ApprovalGateDecision(
            can_publish=False,
            final_status="NEEDS_REVISION",
            reason="Reviewer requested revision.",
            reviewer="admin",
            notes="ปรับโพสต์ก่อน",
        )

    def test_draft_only_never_calls_transport(self) -> None:
        transport = FakeFacebookTransport()
        result = publish_review_package(
            self.review,
            self.approved,
            post_mode="draft_only",
            dry_run=False,
            page_id="123",
            access_token="token",
            transport=transport,
        )

        self.assertFalse(result.attempted)
        self.assertEqual(result.status, "PENDING_REVIEW")
        self.assertEqual(transport.calls, [])

    def test_unapproved_review_blocks_publish(self) -> None:
        transport = FakeFacebookTransport()
        result = publish_review_package(
            self.review,
            self.blocked,
            post_mode="approve_then_post",
            dry_run=False,
            page_id="123",
            access_token="token",
            transport=transport,
        )

        self.assertFalse(result.attempted)
        self.assertEqual(result.status, "NEEDS_REVISION")
        self.assertEqual(transport.calls, [])

    def test_dry_run_skips_real_publish(self) -> None:
        transport = FakeFacebookTransport()
        result = publish_review_package(
            self.review,
            self.approved,
            post_mode="approve_then_post",
            dry_run=True,
            page_id="123",
            access_token="token",
            transport=transport,
        )

        self.assertFalse(result.attempted)
        self.assertEqual(result.status, "PUBLISHED")
        self.assertEqual(transport.calls, [])
        self.assertEqual(result.response_payload["dry_run"], True)

    def test_approved_post_calls_transport(self) -> None:
        transport = FakeFacebookTransport()
        result = publish_review_package(
            self.review,
            self.approved,
            post_mode="approve_then_post",
            dry_run=False,
            page_id="123",
            access_token="token",
            transport=transport,
        )

        self.assertTrue(result.attempted)
        self.assertEqual(result.status, "PUBLISHED")
        self.assertEqual(result.published_post_id, "fb_post_123")
        self.assertEqual(len(transport.calls), 1)

    def test_approved_schedule_calls_transport(self) -> None:
        transport = FakeFacebookTransport()
        scheduled_at = datetime(2026, 4, 21, 9, 0, tzinfo=UTC)
        result = publish_review_package(
            self.review,
            self.approved,
            post_mode="approve_then_schedule",
            dry_run=False,
            page_id="123",
            access_token="token",
            transport=transport,
            scheduled_publish_at=scheduled_at,
        )

        self.assertTrue(result.attempted)
        self.assertEqual(result.status, "SCHEDULED")
        self.assertEqual(result.scheduled_publish_time, scheduled_at.isoformat())
        self.assertEqual(len(transport.calls), 1)

    def test_missing_schedule_time_fails_safely(self) -> None:
        transport = FakeFacebookTransport()
        result = publish_review_package(
            self.review,
            self.approved,
            post_mode="approve_then_schedule",
            dry_run=False,
            page_id="123",
            access_token="token",
            transport=transport,
        )

        self.assertFalse(result.attempted)
        self.assertEqual(result.status, "APPROVED")
        self.assertEqual(transport.calls, [])

    def test_publish_failure_is_logged_as_non_success(self) -> None:
        result = publish_review_package(
            self.review,
            self.approved,
            post_mode="approve_then_post",
            dry_run=False,
            page_id="123",
            access_token="token",
            transport=FailingFacebookTransport(),
        )

        self.assertTrue(result.attempted)
        self.assertEqual(result.status, "APPROVED")
        self.assertIn("failed", result.reason.lower())
        self.assertIsNotNone(result.error_message)

    def test_publish_log_is_written(self) -> None:
        settings = load_settings(env={})
        ensure_runtime_dirs(settings)
        transport = FakeFacebookTransport()
        result = publish_review_package(
            self.review,
            self.approved,
            post_mode="approve_then_post",
            dry_run=True,
            page_id="123",
            access_token="token",
            transport=transport,
        )

        path = write_publish_log(result, self.review, settings.logs_dir, written_at=datetime(2026, 4, 20, 2, 0, tzinfo=UTC))
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "PUBLISHED")
        self.assertEqual(payload["run_date"], "2026-04-20")


if __name__ == "__main__":
    unittest.main()
