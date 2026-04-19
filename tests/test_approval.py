"""Tests for the manual approval workflow."""

from __future__ import annotations

import json
import unittest
from datetime import date

from math_content_agent.approval import (
    ApprovalValidationError,
    evaluate_approval,
    load_approval,
    parse_approval_payload,
    write_approval_template,
)
from math_content_agent.config import ensure_runtime_dirs, load_settings
from math_content_agent.models import ApprovalRecord, ReviewPackage
from math_content_agent.package_builder import apply_approval_to_review


class ApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = ReviewPackage(
            run_date=date(2026, 4, 20),
            content_mode="STANDARD_MATH_MODE",
            proposed_topic="Gauss กับจุดเปลี่ยนของทฤษฎีจำนวน",
            why_relevant="วันที่ 2026-04-20 ตรงกับธีมวันจันทร์ของเพจ",
            thai_draft="ร่างโพสต์ภาษาไทย",
            fact_summary=["ข้อเท็จจริงที่ผ่านการตรวจสอบ"],
            short_references=["AMS - Gauss biography"],
            full_references=["AMS. Gauss biography. https://www.ams.org/gauss"],
            verification_notes=["พร้อมให้ผู้ดูแลตรวจ"],
            confidence=0.90,
            status="PENDING_REVIEW",
        )

    def test_parse_approval_payload_accepts_valid_approval(self) -> None:
        approval = parse_approval_payload(
            {
                "date": "2026-04-20",
                "status": "approved",
                "reviewer": "admin",
                "notes": "พร้อมโพสต์",
                "decided_at": "2026-04-20T09:15:00+07:00",
            }
        )

        self.assertEqual(approval.status, "APPROVED")
        self.assertEqual(approval.reviewer, "admin")

    def test_parse_approval_payload_rejects_invalid_status(self) -> None:
        with self.assertRaises(ApprovalValidationError):
            parse_approval_payload(
                {
                    "date": "2026-04-20",
                    "status": "PUBLISH_NOW",
                    "reviewer": "admin",
                }
            )

    def test_approval_template_is_written(self) -> None:
        settings = load_settings(env={})
        ensure_runtime_dirs(settings)

        path = write_approval_template(self.review, settings.approval_dir)
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "PENDING_REVIEW")
        self.assertEqual(payload["date"], "2026-04-20")

    def test_load_approval_reads_file(self) -> None:
        settings = load_settings(env={})
        ensure_runtime_dirs(settings)
        path = settings.approval_dir / "2026-04-20_approval_test.json"
        path.write_text(
            json.dumps(
                {
                    "date": "2026-04-20",
                    "status": "APPROVED",
                    "reviewer": "admin",
                    "notes": "OK",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        approval = load_approval(path)
        self.assertEqual(approval.status, "APPROVED")
        self.assertEqual(approval.notes, "OK")

    def test_approved_review_allows_publish(self) -> None:
        decision = evaluate_approval(
            self.review,
            ApprovalRecord(
                run_date=date(2026, 4, 20),
                status="APPROVED",
                reviewer="admin",
                notes="พร้อมโพสต์",
            ),
        )

        self.assertTrue(decision.can_publish)
        self.assertEqual(decision.final_status, "APPROVED")

    def test_revision_request_blocks_publish(self) -> None:
        decision = evaluate_approval(
            self.review,
            ApprovalRecord(
                run_date=date(2026, 4, 20),
                status="NEEDS_REVISION",
                reviewer="admin",
                notes="ช่วยปรับน้ำเสียงให้กระชับขึ้น",
            ),
        )

        self.assertFalse(decision.can_publish)
        self.assertEqual(decision.final_status, "NEEDS_REVISION")

    def test_mismatched_date_fails_safely(self) -> None:
        decision = evaluate_approval(
            self.review,
            ApprovalRecord(
                run_date=date(2026, 4, 21),
                status="APPROVED",
                reviewer="admin",
                notes="พร้อมโพสต์",
            ),
        )

        self.assertFalse(decision.can_publish)
        self.assertIn("does not match", decision.reason)

    def test_apply_approval_to_review_updates_status_and_notes(self) -> None:
        updated = apply_approval_to_review(
            self.review,
            ApprovalRecord(
                run_date=date(2026, 4, 20),
                status="NEEDS_REVISION",
                reviewer="admin",
                notes="ช่วยเพิ่มคำอธิบายสั้น ๆ สำหรับผู้อ่านทั่วไป",
            ),
        )

        self.assertEqual(updated.status, "NEEDS_REVISION")
        self.assertTrue(any("Reviewer note" in note for note in updated.verification_notes))


if __name__ == "__main__":
    unittest.main()
