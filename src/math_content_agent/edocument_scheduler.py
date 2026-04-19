"""CLI entrypoint for the read-only eDocument digest workflow."""

from __future__ import annotations

import argparse
import os
import traceback
from datetime import date, datetime
from pathlib import Path

from .config import ensure_runtime_dirs, load_settings
from .edocument_client import EDocumentClient
from .edocument_digest import build_digest_email, render_digest_json
from .emailer import send_review_email
from .utils import normalize_now


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for eDocument digest runs."""

    parser = argparse.ArgumentParser(description="Read-only eDocument digest runner.")
    parser.add_argument("--now", dest="now", help="Optional ISO timestamp for manual testing.")
    parser.add_argument("--config-dir", dest="config_dir", type=Path, help="Optional alternate config directory.")
    parser.add_argument("--lookback-days", dest="lookback_days", type=int, help="Days to look back from the run date.")
    parser.add_argument("--max-documents", dest="max_documents", type=int, help="Maximum matching documents to summarize.")
    parser.add_argument("--headed", dest="headed", action="store_true", help="Launch the browser in headed mode.")
    parser.add_argument("--skip-email", dest="skip_email", action="store_true", help="Build the digest but do not send email.")
    return parser


def _parse_now(raw_value: str | None) -> datetime | None:
    if raw_value is None:
        return None
    return datetime.fromisoformat(raw_value)


def _load_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _resolve_smtp_config() -> dict[str, object]:
    sender = os.environ.get("EMAIL_FROM") or os.environ.get("SMTP_USERNAME")
    recipient = os.environ.get("EDOC_EMAIL_TO") or os.environ.get("REVIEW_EMAIL_TO")
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    missing = [
        name
        for name, value in (
            ("SMTP_HOST", smtp_host),
            ("SMTP_USERNAME", smtp_username),
            ("SMTP_PASSWORD", smtp_password),
            ("EMAIL_FROM/SMTP_USERNAME", sender),
            ("EDOC_EMAIL_TO/REVIEW_EMAIL_TO", recipient),
        )
        if not value
    ]
    if missing:
        raise ValueError("Missing required email configuration: " + ", ".join(missing))

    return {
        "sender": sender,
        "recipient": recipient,
        "smtp_host": smtp_host,
        "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
        "smtp_username": smtp_username,
        "smtp_password": smtp_password,
        "use_tls": os.environ.get("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"},
    }


def _write_digest_log(run_json: str, settings, run_date: date) -> Path:
    path = settings.logs_dir / f"{run_date.isoformat()}_edocument_digest.json"
    path.write_text(run_json, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    """Run one read-only eDocument digest cycle."""

    parser = build_parser()
    args = parser.parse_args(argv)
    settings = load_settings(config_dir=args.config_dir)
    ensure_runtime_dirs(settings)

    run_at = normalize_now(_parse_now(args.now), settings.timezone)
    login_url = os.environ.get("EDOC_LOGIN_URL", "https://sru.e-office.cloud/api/auth/login")
    lookback_days = args.lookback_days if args.lookback_days is not None else int(os.environ.get("EDOC_LOOKBACK_DAYS", "1"))
    max_documents = args.max_documents if args.max_documents is not None else int(os.environ.get("EDOC_MAX_DOCUMENTS", "10"))

    client = EDocumentClient(
        username=_load_required_env("EDOC_USERNAME"),
        password=_load_required_env("EDOC_PASSWORD"),
        login_url=login_url,
        headless=not args.headed,
    )
    digest_run = client.collect_digest(run_at=run_at, lookback_days=lookback_days, max_documents=max_documents)

    log_path = _write_digest_log(render_digest_json(digest_run), settings, run_at.date())
    print(f"Digest status: {digest_run.status}")
    print(f"Scanned rows: {digest_run.scanned_rows}")
    print(f"Matched documents: {len(digest_run.matched_documents)}")
    print(f"Log path: {log_path}")

    if args.skip_email:
        print("Email skipped by flag.")
        return 0

    smtp_config = _resolve_smtp_config()
    message = build_digest_email(
        digest_run,
        recipient=str(smtp_config["recipient"]),
        sender=str(smtp_config["sender"]),
    )
    try:
        send_review_email(
            message=message,
            smtp_host=str(smtp_config["smtp_host"]),
            smtp_port=int(smtp_config["smtp_port"]),
            smtp_username=str(smtp_config["smtp_username"]),
            smtp_password=str(smtp_config["smtp_password"]),
            use_tls=bool(smtp_config["use_tls"]),
        )
    except Exception as exc:
        print(f"Email send failed: {exc}")
        traceback.print_exc()
        raise
    print(f"Emailed eDocument digest to {smtp_config['recipient']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
