"""Tests for daily review email composition."""

from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from math_content_agent.emailer import build_review_email
from math_content_agent.models import ReviewPackage


class EmailerTests(unittest.TestCase):
    def test_build_review_email_includes_subject_body_and_attachments(self) -> None:
        review = ReviewPackage(
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
        with TemporaryDirectory() as temp_dir:
            markdown_path = Path(temp_dir) / "2026-04-20_review.md"
            json_path = Path(temp_dir) / "2026-04-20_review.json"
            markdown_path.write_text("# Review", encoding="utf-8")
            json_path.write_text("{}", encoding="utf-8")

            message = build_review_email(
                review=review,
                markdown_path=markdown_path,
                json_path=json_path,
                sender="sender@example.com",
                recipient="lordtd@gmail.com",
            )

        self.assertIn("2026-04-20", message["Subject"])
        self.assertEqual(message["To"], "lordtd@gmail.com")
        self.assertEqual(len(list(message.iter_attachments())), 2)


if __name__ == "__main__":
    unittest.main()
