"""Tests for eDocument parsing and email rendering."""

from __future__ import annotations

import unittest
from datetime import date, datetime

from math_content_agent.edocument_digest import (
    build_digest_email,
    extract_attachment_names,
    extract_label_value,
    parse_buddhist_date,
    parse_listing_row,
    should_include_entry,
    summarize_document,
)
from math_content_agent.models import EDocumentDetail, EDocumentDigestDocument, EDocumentDigestRun
from math_content_agent.utils import get_timezone


class EDocumentDigestTests(unittest.TestCase):
    def test_parse_buddhist_date_converts_to_gregorian(self) -> None:
        self.assertEqual(parse_buddhist_date("17/4/2569"), date(2026, 4, 17))

    def test_parse_listing_row_extracts_key_fields(self) -> None:
        row = (
            "- รับ **ดิจิทัล** สนอ.0227/2569 17/4/2569 ด่วนที่สุดนำส่งประกาศมหาวิทยาลัยราชภัฏสุราษฎร์ธานี "
            "เรื่อง แนวทางการจัดการเรียนการสอน และการปฏิบัติงานของบุคลากร เพื่อให้เป็นไปตามมาตรการลดการใช้พลังงานของหน่วยงานภาครัฐ "
            "(ฉบับที่ 2) จาก สำนักงานอธิการบดี เรียน คณบดี ผู้อำนวยการสำนัก/สถาบัน ผู้อำนวยกอง หัวหน้าหน่วยงาน "
            "เล่มทะเบียนต้นทาง : (สำนักงานอธิการบดี) แฟ้มส่ง ภายใน เล่มทะเบียนที่ส่งมา : (คณะวิทยาศาสตร์ฯ) แฟ้มรับ ภายใน "
            "วันที่ส่ง : 17/4/2569 12:50 น. รอรับ"
        )
        entry = parse_listing_row(1, row)

        self.assertEqual(entry.document_number, "สนอ.0227/2569")
        self.assertEqual(entry.document_date, "17/4/2569")
        self.assertEqual(entry.sent_date, date(2026, 4, 17))
        self.assertEqual(entry.status, "รอรับ")
        self.assertEqual(entry.urgency, "ด่วนที่สุด")
        self.assertEqual(entry.sender, "สำนักงานอธิการบดี")
        self.assertIn("แนวทางการจัดการเรียนการสอน", entry.subject)

    def test_should_include_entry_uses_lookback_window(self) -> None:
        run_date = date(2026, 4, 19)
        entry = parse_listing_row(
            1,
            "- รับ **ดิจิทัล** ทดสอบ/1 18/4/2569 เรื่องทดสอบ จาก หน่วยงาน เรียน ผู้รับ "
            "เล่มทะเบียนต้นทาง : x เล่มทะเบียนที่ส่งมา : y วันที่ส่ง : 18/4/2569 09:00 น. รอรับ",
        )

        self.assertTrue(should_include_entry(entry, run_date, 1))
        self.assertFalse(should_include_entry(entry, run_date, 0))

    def test_extract_label_value_and_attachments(self) -> None:
        lines = [
            "รายละเอียดเอกสาร",
            "เลขที่หนังสือ :",
            "สนอ.0227/2569",
            "เรื่อง :",
            "นำส่งประกาศ",
            "ประกาศมหาวิทยาลัยราชภัฏสุราษฎร์ธานี ฉบับที่ 2.pdf",
            "เอกสารประกอบ.xlsx",
        ]

        self.assertEqual(extract_label_value(lines, "เลขที่หนังสือ :"), "สนอ.0227/2569")
        self.assertEqual(
            extract_attachment_names(lines),
            ["ประกาศมหาวิทยาลัยราชภัฏสุราษฎร์ธานี ฉบับที่ 2.pdf", "เอกสารประกอบ.xlsx"],
        )

    def test_build_digest_email_for_no_matches(self) -> None:
        bangkok = get_timezone("Asia/Bangkok")
        digest_run = EDocumentDigestRun(
            run_at=datetime(2026, 4, 19, 11, 30, tzinfo=bangkok),
            run_date=date(2026, 4, 19),
            lookback_days=1,
            login_url="https://sru.e-office.cloud/api/auth/login",
            status="ok",
            scanned_rows=10,
            matched_documents=[],
            errors=[],
        )

        message = build_digest_email(
            digest_run,
            recipient="review-recipient@example.com",
            sender="sender@example.com",
        )

        body = message.get_body(preferencelist=("plain",)).get_content()
        self.assertIn("ไม่พบเอกสารใหม่", message["Subject"])
        self.assertIn("ไม่พบเอกสารใหม่ตามเงื่อนไข", body)

    def test_summarize_document_uses_detail_fields(self) -> None:
        entry = parse_listing_row(
            1,
            "- รับ **ดิจิทัล** ทดสอบ/1 18/4/2569 เรื่องทดสอบ จาก หน่วยงาน เรียน ผู้รับ "
            "เล่มทะเบียนต้นทาง : x เล่มทะเบียนที่ส่งมา : y วันที่ส่ง : 18/4/2569 09:00 น. รอรับ",
        )
        detail = EDocumentDetail(
            detail_url="https://example.com/detail/1",
            document_number="ทดสอบ/1",
            document_date="18/4/2569",
            subject="เรื่องทดสอบ",
            sender="หน่วยงาน",
            recipient="ผู้รับ",
            urgency="ด่วน",
            purpose="เพื่อโปรดทราบ",
            detail_note="มีไฟล์แนบ 2 รายการ",
            attachment_names=["test.pdf"],
        )
        document = EDocumentDigestDocument(listing=entry, detail=detail)

        summary = summarize_document(document)

        self.assertIn("เลขที่หนังสือ: ทดสอบ/1", summary)
        self.assertIn("ชั้นความเร็ว: ด่วน", summary)
        self.assertIn("ไฟล์แนบ: test.pdf", summary)


if __name__ == "__main__":
    unittest.main()
