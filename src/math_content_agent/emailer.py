"""Email delivery for generated review packages."""

from __future__ import annotations

import argparse
import os
import smtplib
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path

from .config import load_settings
from .package_builder import load_review_package
from .utils import normalize_now


def build_review_email(
    *,
    review,
    markdown_path: Path,
    json_path: Path,
    sender: str,
    recipient: str,
) -> EmailMessage:
    """Build the outbound email for a daily review package."""

    subject = f"Daily Math Review - {review.run_date.isoformat()} - {review.status}"
    body = "\n".join(
        [
            f"Topic: {review.proposed_topic}",
            f"Status: {review.status}",
            f"Confidence: {review.confidence:.2f}",
            f"Date Relevance Type: {review.date_relevance_type}",
            "",
            "Why this matches today:",
            review.why_relevant,
            "",
            "Duplicate Check:",
            *([f"- {item}" for item in review.duplicate_notes] if review.duplicate_notes else ["- No recent duplicate match found."]),
            "",
            "Draft Facebook Post:",
            review.thai_draft,
            "",
            "Short References:",
            *[f"- {item}" for item in review.short_references],
            "",
            "Verification Notes:",
            *[f"- {item}" for item in review.verification_notes],
        ]
    )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)

    message.add_attachment(
        markdown_path.read_bytes(),
        maintype="text",
        subtype="markdown",
        filename=markdown_path.name,
    )
    message.add_attachment(
        json_path.read_bytes(),
        maintype="application",
        subtype="json",
        filename=json_path.name,
    )
    return message


def send_review_email(
    *,
    message: EmailMessage,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    use_tls: bool = True,
) -> None:
    """Send the review email via SMTP."""

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        smtp.ehlo()
        if use_tls:
            smtp.starttls()
            smtp.ehlo()
        smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)


def _default_review_date(config_dir: Path | None = None) -> date:
    """Resolve the default review date in the configured timezone."""

    settings = load_settings(config_dir=config_dir)
    now = normalize_now(None, settings.timezone)
    return now.date()


def _parse_review_date(raw_value: str | None, config_dir: Path | None = None) -> date:
    """Parse a review date or fall back to today in the configured timezone."""

    if raw_value is None:
        return _default_review_date(config_dir=config_dir)
    return date.fromisoformat(raw_value)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for review emailing."""

    parser = argparse.ArgumentParser(description="Email the generated daily review package.")
    parser.add_argument("--review-date", dest="review_date", help="Optional review date in YYYY-MM-DD format.")
    parser.add_argument("--config-dir", dest="config_dir", type=Path, help="Optional alternate config directory.")
    parser.add_argument("--to", dest="recipient", help="Override the recipient email address.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for emailing the daily review package."""

    parser = build_parser()
    args = parser.parse_args(argv)
    settings = load_settings(config_dir=args.config_dir)
    review_date = _parse_review_date(args.review_date, config_dir=args.config_dir)
    review_json_path = settings.verification_json_dir / f"{review_date.isoformat()}_review.json"
    review_markdown_path = settings.daily_review_dir / f"{review_date.isoformat()}_review.md"

    review = load_review_package(review_json_path)
    sender = os.environ.get("EMAIL_FROM") or os.environ.get("SMTP_USERNAME")
    recipient = args.recipient or os.environ.get("REVIEW_EMAIL_TO")
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}

    missing = [
        name
        for name, value in (
            ("SMTP_HOST", smtp_host),
            ("SMTP_USERNAME", smtp_username),
            ("SMTP_PASSWORD", smtp_password),
            ("EMAIL_FROM/SMTP_USERNAME", sender),
            ("REVIEW_EMAIL_TO", recipient),
        )
        if not value
    ]
    if missing:
        parser.error(f"Missing required email configuration: {', '.join(missing)}")

    message = build_review_email(
        review=review,
        markdown_path=review_markdown_path,
        json_path=review_json_path,
        sender=sender,
        recipient=recipient,
    )
    send_review_email(
        message=message,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        use_tls=use_tls,
    )
    print(f"Emailed review for {review.run_date.isoformat()} to {recipient}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
