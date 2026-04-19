"""Browser automation client for the read-only eDocument digest flow."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from .edocument_attachments import extract_attachment_preview
from .edocument_digest import (
    extract_attachment_names,
    extract_label_value,
    parse_listing_row,
    should_include_entry,
    summarize_document,
)
from .models import EDocumentDetail, EDocumentDigestDocument, EDocumentDigestRun


class EDocumentClient:
    """Collect matching Saraban documents using Playwright."""

    def __init__(
        self,
        *,
        username: str,
        password: str,
        login_url: str,
        headless: bool = True,
        page_timeout_ms: int = 60_000,
    ) -> None:
        self._username = username
        self._password = password
        self._login_url = login_url
        self._headless = headless
        self._page_timeout_ms = page_timeout_ms

    def collect_digest(
        self,
        *,
        run_at: datetime,
        lookback_days: int,
        max_documents: int,
    ) -> EDocumentDigestRun:
        """Log in, scan the pending list, and gather read-only summaries."""

        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        scanned_rows = 0
        matched_documents: list[EDocumentDigestDocument] = []
        errors: list[str] = []

        with TemporaryDirectory(prefix="edoc-digest-") as temp_dir:
            download_dir = Path(temp_dir)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self._headless)
                context = browser.new_context(viewport={"width": 1440, "height": 960}, accept_downloads=True)
                page = context.new_page()
                page.set_default_timeout(self._page_timeout_ms)
                try:
                    self._login(page)
                    list_url = self._open_saraban(page)
                    row_texts = self._list_rows(page)
                    scanned_rows = len(row_texts)

                    matching_indexes: list[int] = []
                    for row_index, row_text in row_texts:
                        entry = parse_listing_row(row_index=row_index, row_text=row_text)
                        if should_include_entry(entry, run_at.date(), lookback_days):
                            matching_indexes.append(row_index)
                        if len(matching_indexes) >= max_documents:
                            break

                    for row_index in matching_indexes:
                        try:
                            document = self._collect_document(
                                page,
                                list_url=list_url,
                                row_index=row_index,
                                download_dir=download_dir,
                            )
                            matched_documents.append(replace(document, summary_points=summarize_document(document)))
                        except PlaywrightTimeoutError as exc:
                            errors.append(f"เปิดเอกสารแถวที่ {row_index} ไม่สำเร็จ: {exc}")
                            page.goto(list_url, wait_until="networkidle")
                        except Exception as exc:  # pragma: no cover - live portal failure path
                            errors.append(f"แถวที่ {row_index} เกิดข้อผิดพลาด: {exc}")
                            page.goto(list_url, wait_until="networkidle")
                finally:
                    browser.close()

        status = "ok" if not errors else ("partial_success" if matched_documents or scanned_rows else "error")
        return EDocumentDigestRun(
            run_at=run_at,
            run_date=run_at.date(),
            lookback_days=lookback_days,
            login_url=self._login_url,
            status=status,
            scanned_rows=scanned_rows,
            matched_documents=matched_documents,
            errors=errors,
        )

    def _login(self, page) -> None:
        page.goto(self._login_url, wait_until="networkidle")
        page.fill("#username", self._username)
        page.fill("#password", self._password)
        page.locator("button").click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2_000)

        current_url = page.url.lower()
        body_text = page.locator("body").inner_text()
        if "/api/auth/login" in current_url or "เข้าสู่ระบบ" in body_text:
            raise RuntimeError("Login did not complete successfully on the runner.")

    def _open_saraban(self, page) -> str:
        page.goto("https://sru.e-office.cloud/saraban", wait_until="networkidle")
        page.wait_for_timeout(2_000)
        body_text = page.locator("body").inner_text()
        if "หนังสือรับ" not in body_text and "รอรับ" not in body_text and "ไม่มีรายการ" not in body_text:
            body_preview = " ".join(body_text.split())[:300]
            raise RuntimeError(f"Saraban page did not load expected content. url={page.url} preview={body_preview}")
        return page.url

    def _list_rows(self, page) -> list[tuple[int, str]]:
        rows = page.locator("table tr").all_inner_texts()
        cleaned_rows: list[tuple[int, str]] = []
        for row_index, text in enumerate(rows[1:], start=1):
            compact = " ".join(text.split())
            if compact and compact != "ไม่มีรายการ":
                cleaned_rows.append((row_index, compact))
        return cleaned_rows

    def _collect_document(self, page, *, list_url: str, row_index: int, download_dir: Path) -> EDocumentDigestDocument:
        page.goto(list_url, wait_until="networkidle")
        page.wait_for_timeout(1_500)
        row_text = " ".join(page.locator("table tr").nth(row_index).inner_text().split())
        listing = parse_listing_row(row_index=row_index, row_text=row_text)
        page.locator("table tr").nth(row_index).click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1_500)

        lines = self._body_lines(page)
        detail = self._extract_detail(page.url, lines)

        warnings: list[str] = []
        open_files = page.get_by_text("เปิดแฟ้มไฟล์", exact=False)
        if open_files.count():
            open_files.first.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1_500)
            attachments = extract_attachment_names(self._body_lines(page))
            attachment_summaries = self._download_and_summarize_attachments(page, download_dir, warnings)
            detail = replace(detail, attachment_names=attachments, attachment_summaries=attachment_summaries)
            if not attachments:
                warnings.append("ไม่สามารถดึงรายชื่อไฟล์แนบจากหน้าแฟ้มเอกสารได้")
        else:
            warnings.append("ไม่พบปุ่มเปิดแฟ้มไฟล์บนหน้าเอกสาร")

        return EDocumentDigestDocument(listing=listing, detail=detail, warnings=warnings)

    def _body_lines(self, page) -> list[str]:
        return [line.strip() for line in page.locator("body").inner_text().splitlines() if line.strip()]

    def _extract_detail(self, detail_url: str, lines: list[str]) -> EDocumentDetail:
        return EDocumentDetail(
            detail_url=detail_url,
            document_number=extract_label_value(lines, "เลขที่หนังสือ :"),
            document_date=extract_label_value(lines, "ลงวันที่ :"),
            subject=extract_label_value(lines, "เรื่อง :") or "-",
            sender=extract_label_value(lines, "จาก :"),
            recipient=extract_label_value(lines, "เรียนถึง :"),
            urgency=extract_label_value(lines, "ชั้นความเร็ว :"),
            purpose=extract_label_value(lines, "เพื่อ :"),
            detail_note=extract_label_value(lines, "รายละเอียดเพิ่มเติม :"),
        )

    def _download_and_summarize_attachments(self, page, download_dir: Path, warnings: list[str]) -> list[str]:
        item_locators = page.locator('[id^="prep-file-list-"]')
        total = item_locators.count()
        summaries: list[str] = []
        download_button = page.locator("#prep-download-file-btn")

        for index in range(total):
            item_locators.nth(index).click()
            page.wait_for_timeout(1_500)

            if download_button.count() == 0 or download_button.is_disabled():
                warnings.append(f"ไฟล์แนบลำดับ {index + 1} ไม่สามารถกดดาวน์โหลดได้")
                continue

            try:
                with page.expect_download(timeout=15_000) as download_info:
                    download_button.click()
                download = download_info.value
            except Exception as exc:  # pragma: no cover - live portal failure path
                warnings.append(f"ดาวน์โหลดไฟล์แนบลำดับ {index + 1} ไม่สำเร็จ: {exc}")
                continue

            suggested_name = download.suggested_filename
            safe_name = suggested_name.replace("\\", "_").replace("/", "_")
            target_path = download_dir / safe_name
            download.save_as(target_path)
            try:
                preview = extract_attachment_preview(target_path)
                if preview:
                    summaries.append(f"{suggested_name}: {preview}")
                else:
                    warnings.append(f"อ่านไฟล์แนบได้แต่ดึงข้อความสำคัญไม่ได้: {suggested_name}")
            except Exception as exc:  # pragma: no cover - depends on file type/content
                warnings.append(f"อ่านไฟล์แนบไม่สำเร็จ {suggested_name}: {exc}")
        return summaries
