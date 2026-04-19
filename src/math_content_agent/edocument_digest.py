"""Pure helpers for parsing and rendering eDocument digest runs."""

from __future__ import annotations

import re
from dataclasses import asdict
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from typing import Iterable

from .models import EDocumentDetail, EDocumentDigestDocument, EDocumentDigestRun, EDocumentListEntry

_DATE_PATTERN = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_ATTACHMENT_PATTERN = re.compile(r"(?i)\.(pdf|doc|docx|xls|xlsx|csv)\b")


def parse_buddhist_date(raw_value: str | None) -> date | None:
    """Convert a DD/MM/YYYY portal date into Gregorian date."""

    if not raw_value:
        return None
    match = _DATE_PATTERN.search(raw_value)
    if not match:
        return None

    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3))
    if year >= 2400:
        year -= 543
    return date(year, month, day)


def _clean(value: str | None) -> str | None:
    """Normalize portal text into a compact single-line value."""

    if value is None:
        return None
    cleaned = " ".join(value.split()).strip(" -")
    return cleaned or None


def parse_listing_row(row_index: int, row_text: str) -> EDocumentListEntry:
    """Extract structured metadata from one Saraban list row."""

    compact = " ".join(row_text.split())
    document_number_match = re.search(r"\*\*ดิจิทัล\*\*\s+(\S+)", compact)
    sent_at_match = re.search(r"วันที่ส่ง\s*:\s*([0-9/]+(?:\s+\d{1,2}:\d{2}\s*น\.)?)", compact)
    document_date_match = re.search(r"\*\*ดิจิทัล\*\*\s+\S+\s+([0-9/]+)", compact)
    urgency_match = re.search(r"(ด่วนที่สุด|ด่วนมาก|ด่วน)", compact)

    sender = None
    sender_match = re.search(r"\sจาก\s+(.+?)\sเรียน\s", compact)
    if sender_match:
        sender = _clean(sender_match.group(1))

    recipient = None
    recipient_match = re.search(r"\sเรียน\s+(.+?)\sเล่มทะเบียนต้นทาง\s*:", compact)
    if recipient_match:
        recipient = _clean(recipient_match.group(1))

    subject = compact
    subject_match = re.search(r"\*\*ดิจิทัล\*\*\s+\S+\s+[0-9/]+\s+(.+?)\sจาก\s", compact)
    if subject_match:
        subject = _clean(subject_match.group(1)) or compact

    return EDocumentListEntry(
        row_index=row_index,
        raw_text=compact,
        document_number=document_number_match.group(1) if document_number_match else None,
        document_date=document_date_match.group(1) if document_date_match else None,
        subject=subject,
        sender=sender,
        recipient=recipient,
        sent_at=sent_at_match.group(1) if sent_at_match else None,
        sent_date=parse_buddhist_date(sent_at_match.group(1) if sent_at_match else None),
        status="รอรับ" if "รอรับ" in compact else "อื่นๆ",
        urgency=urgency_match.group(1) if urgency_match else None,
    )


def should_include_entry(entry: EDocumentListEntry, run_date: date, lookback_days: int) -> bool:
    """Return True when a list entry matches the digest window and status."""

    if entry.status != "รอรับ" or entry.sent_date is None:
        return False
    oldest_date = run_date - timedelta(days=lookback_days)
    return oldest_date <= entry.sent_date <= run_date


def extract_label_value(lines: Iterable[str], label: str) -> str | None:
    """Return the first value that follows a label in the detail page text."""

    values = [line.strip() for line in lines if line and line.strip()]
    for index, line in enumerate(values):
        if line == label and index + 1 < len(values):
            return _clean(values[index + 1])
        if line.startswith(label):
            return _clean(line[len(label) :])
    return None


def extract_attachment_names(lines: Iterable[str]) -> list[str]:
    """Collect likely attachment filenames from the file-list page."""

    seen: set[str] = set()
    attachment_names: list[str] = []
    for line in lines:
        cleaned = _clean(line)
        if not cleaned or not _ATTACHMENT_PATTERN.search(cleaned):
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        attachment_names.append(cleaned)
    return attachment_names


def summarize_document(document: EDocumentDigestDocument) -> list[str]:
    """Build concise Thai summary points for one matched document."""

    entry = document.listing
    detail = document.detail
    summary = [
        f"เลขที่หนังสือ: {detail.document_number if detail and detail.document_number else entry.document_number or '-'}",
        f"เรื่อง: {detail.subject if detail and detail.subject else entry.subject}",
        f"ผู้ส่ง: {detail.sender if detail and detail.sender else entry.sender or '-'}",
        f"วันที่ส่ง: {entry.sent_at or '-'}",
    ]

    urgency = detail.urgency if detail and detail.urgency else entry.urgency
    if urgency:
        summary.append(f"ชั้นความเร็ว: {urgency}")

    recipient = detail.recipient if detail and detail.recipient else entry.recipient
    if recipient:
        summary.append(f"เรียนถึง: {recipient}")

    if detail and detail.purpose and detail.purpose != "-":
        summary.append(f"เพื่อ: {detail.purpose}")

    if detail and detail.detail_note and detail.detail_note != "-":
        summary.append(f"หมายเหตุสำคัญ: {detail.detail_note}")

    if detail and detail.attachment_names:
        summary.append("ไฟล์แนบ: " + ", ".join(detail.attachment_names))
    else:
        summary.append("ไฟล์แนบ: ไม่พบไฟล์แนบที่อ่านได้จากหน้าแฟ้มเอกสาร")

    if detail and detail.attachment_summaries:
        for attachment_summary in detail.attachment_summaries[:3]:
            summary.append("สาระจากไฟล์แนบ: " + attachment_summary)

    return summary


def build_digest_email(run: EDocumentDigestRun, recipient: str, sender: str) -> EmailMessage:
    """Render the outbound email message for one digest run."""

    if run.matched_documents:
        subject = f"สรุป eDocument: พบ {len(run.matched_documents)} เอกสาร ({run.run_date.isoformat()})"
        sections: list[str] = []
        for index, document in enumerate(run.matched_documents, start=1):
            points = document.summary_points or summarize_document(document)
            section = "\n".join(f"- {point}" for point in points)
            sections.append(f"{index}. {document.listing.subject}\n{section}")
        body = "\n\n".join(
            [
                "สรุปการตรวจสอบ eDocument รอบนี้",
                "",
                f"ตรวจสอบเฉพาะเอกสารที่ส่งในช่วง {run.lookback_days + 1} วันล่าสุดและยังอยู่ในสถานะรอรับ",
                "",
                *sections,
                "",
                "หมายเหตุ: phase นี้เป็น read-only จึงยังไม่ได้กดรับเอกสารอัตโนมัติ",
            ]
        )
    else:
        subject = f"สรุป eDocument: ไม่พบเอกสารใหม่ ({run.run_date.isoformat()})"
        body = "\n".join(
            [
                "สรุปการตรวจสอบ eDocument รอบนี้",
                "",
                "ตรวจสอบในระบบ SRU eDocument > Saraban แล้ว",
                f"เงื่อนไขที่ใช้ตรวจคือดูเฉพาะเอกสารที่ส่งในช่วง {run.lookback_days + 1} วันล่าสุดและยังอยู่ในสถานะรอรับ",
                "",
                "ผลการตรวจสอบ:",
                "- ไม่พบเอกสารใหม่ตามเงื่อนไข",
                "",
                "หมายเหตุ: phase นี้เป็น read-only จึงยังไม่ได้กดรับเอกสารอัตโนมัติ",
            ]
        )

    if run.errors:
        body += "\n\nปัญหาที่พบระหว่างการรัน:\n" + "\n".join(f"- {error}" for error in run.errors)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)
    return message


def render_digest_json(run: EDocumentDigestRun) -> str:
    """Return a JSON payload suitable for logs and workflow artifacts."""

    import json

    payload = asdict(run)
    payload["run_at"] = run.run_at.isoformat()
    payload["run_date"] = run.run_date.isoformat()
    return json.dumps(payload, ensure_ascii=False, indent=2)
