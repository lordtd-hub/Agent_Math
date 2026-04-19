"""Weekday-aware CLI entrypoint for generation and publishing."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from .config import load_settings
from .orchestrator import generate_daily_review, publish_from_approval
from .runtime import evaluate_run_day


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(description="Weekday scheduler for the math content agent.")
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser("generate-review", help="Generate the daily review package.")
    generate_parser.add_argument(
        "--now",
        dest="now",
        help="Optional ISO timestamp used for local testing, e.g. 2026-04-20T09:00:00+07:00.",
    )
    generate_parser.add_argument(
        "--config-dir",
        dest="config_dir",
        type=Path,
        help="Optional alternate config directory.",
    )

    publish_parser = subparsers.add_parser("publish-approved", help="Publish or schedule an approved review package.")
    publish_parser.add_argument(
        "--review-date",
        dest="review_date",
        required=True,
        help="Review date in YYYY-MM-DD format.",
    )
    publish_parser.add_argument(
        "--scheduled-publish-at",
        dest="scheduled_publish_at",
        help="Optional ISO timestamp for approve_then_schedule mode.",
    )
    publish_parser.add_argument(
        "--config-dir",
        dest="config_dir",
        type=Path,
        help="Optional alternate config directory.",
    )
    return parser


def _parse_now(raw_value: str | None) -> datetime | None:
    """Parse the optional ISO timestamp flag."""

    if raw_value is None:
        return None
    return datetime.fromisoformat(raw_value)


def _parse_review_date(raw_value: str) -> date:
    """Parse the review date flag."""

    return date.fromisoformat(raw_value)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint used by the scheduler command."""

    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "generate-review"

    if command == "generate-review":
        settings = load_settings(config_dir=args.config_dir)
        decision = evaluate_run_day(now=_parse_now(args.now), config_dir=args.config_dir)

        print(f"Date: {decision.run_date.isoformat()} ({decision.weekday_name})")
        print(f"Decision: {'RUN' if decision.should_run else 'SKIP'}")
        print(f"Output language: {settings.output_language}")
        if decision.theme_label:
            print(f"Theme: {decision.theme_label}")
        print(f"Reason: {decision.reason}")

        artifacts = generate_daily_review(now=_parse_now(args.now), config_dir=args.config_dir)
        if artifacts.should_run and artifacts.review is not None:
            print(f"Mode: {artifacts.mode}")
            print(f"Review markdown: {artifacts.review_markdown_path}")
            print(f"Review JSON: {artifacts.review_json_path}")
            print(f"Approval template: {artifacts.approval_template_path}")
            print(f"Evidence bundle: {artifacts.evidence_bundle_path}")
            if artifacts.news_debug_path:
                print(f"News cache: {artifacts.news_debug_path}")
            if artifacts.planner_debug_path:
                print(f"Planner cache: {artifacts.planner_debug_path}")
        return 0

    if command == "publish-approved":
        scheduled_publish_at = _parse_now(args.scheduled_publish_at) if args.scheduled_publish_at else None
        artifacts = publish_from_approval(
            run_date=_parse_review_date(args.review_date),
            scheduled_publish_at=scheduled_publish_at,
            config_dir=args.config_dir,
        )
        print(f"Review JSON: {artifacts.review_json_path}")
        print(f"Approval file: {artifacts.approval_path}")
        print(f"Publish status: {artifacts.publish_result.status}")
        print(f"Reason: {artifacts.publish_result.reason}")
        print(f"Publish log: {artifacts.publish_log_path}")
        return 0

    parser.error(f"Unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
