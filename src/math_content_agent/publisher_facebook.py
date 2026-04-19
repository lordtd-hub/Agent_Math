"""Facebook publishing workflow with approval gating and dry-run support."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import ApprovalGateDecision, PublishResult, ReviewPackage


class FacebookPublishTransport(Protocol):
    """Transport interface for Facebook publishing."""

    def publish_post(
        self,
        *,
        page_id: str,
        access_token: str,
        message: str,
        scheduled_publish_at: datetime | None = None,
    ) -> dict[str, object]:
        """Publish or schedule a post and return the raw API payload."""


class FacebookGraphApiTransport:
    """Minimal Graph API transport using the Python standard library."""

    def __init__(self, base_url: str = "https://graph.facebook.com") -> None:
        self.base_url = base_url.rstrip("/")

    def publish_post(
        self,
        *,
        page_id: str,
        access_token: str,
        message: str,
        scheduled_publish_at: datetime | None = None,
    ) -> dict[str, object]:
        payload = {
            "message": message,
            "access_token": access_token,
        }
        if scheduled_publish_at is not None:
            if scheduled_publish_at.tzinfo is None:
                raise ValueError("Scheduled publish time must be timezone-aware.")
            payload["published"] = "false"
            payload["scheduled_publish_time"] = str(int(scheduled_publish_at.timestamp()))

        endpoint = f"{self.base_url}/{page_id}/feed"
        request = Request(
            endpoint,
            data=urlencode(payload).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Facebook API returned HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"Facebook API request failed: {exc.reason}") from exc


def publish_review_package(
    review: ReviewPackage,
    approval: ApprovalGateDecision,
    *,
    post_mode: str,
    dry_run: bool,
    page_id: str | None,
    access_token: str | None,
    transport: FacebookPublishTransport,
    scheduled_publish_at: datetime | None = None,
) -> PublishResult:
    """Publish or schedule a reviewed post after an explicit approval decision."""

    if post_mode == "draft_only":
        return PublishResult(
            attempted=False,
            status="PENDING_REVIEW",
            reason="Post mode is draft_only, so no Facebook API call will be made.",
            content_mode=review.content_mode,
            post_mode=post_mode,
        )

    if not approval.can_publish:
        return PublishResult(
            attempted=False,
            status=approval.final_status,
            reason=f"Publishing blocked by approval gate: {approval.reason}",
            content_mode=review.content_mode,
            post_mode=post_mode,
            error_message=approval.reason,
        )

    if not page_id or not access_token:
        return PublishResult(
            attempted=False,
            status="APPROVED",
            reason="Publishing cannot proceed because Facebook credentials are missing.",
            content_mode=review.content_mode,
            post_mode=post_mode,
            error_message="Missing FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ACCESS_TOKEN.",
        )

    if post_mode == "approve_then_schedule" and scheduled_publish_at is None:
        return PublishResult(
            attempted=False,
            status="APPROVED",
            reason="approve_then_schedule requires an explicit scheduled publish time.",
            content_mode=review.content_mode,
            post_mode=post_mode,
            error_message="Missing scheduled publish time.",
        )

    if dry_run:
        dry_run_status = "SCHEDULED" if post_mode == "approve_then_schedule" else "PUBLISHED"
        return PublishResult(
            attempted=False,
            status=dry_run_status,
            reason="Dry-run mode is enabled, so the post was not sent to Facebook.",
            content_mode=review.content_mode,
            post_mode=post_mode,
            scheduled_publish_time=scheduled_publish_at.isoformat() if scheduled_publish_at else None,
            response_payload={"dry_run": True, "message_preview": review.thai_draft[:120]},
        )

    try:
        payload = transport.publish_post(
            page_id=page_id,
            access_token=access_token,
            message=review.thai_draft,
            scheduled_publish_at=scheduled_publish_at,
        )
    except Exception as exc:
        return PublishResult(
            attempted=True,
            status="APPROVED",
            reason="Facebook publishing failed after approval.",
            content_mode=review.content_mode,
            post_mode=post_mode,
            scheduled_publish_time=scheduled_publish_at.isoformat() if scheduled_publish_at else None,
            error_message=str(exc),
        )

    final_status = "SCHEDULED" if post_mode == "approve_then_schedule" else "PUBLISHED"
    published_post_id = payload.get("id") if isinstance(payload.get("id"), str) else None
    return PublishResult(
        attempted=True,
        status=final_status,
        reason="Facebook publishing completed successfully.",
        content_mode=review.content_mode,
        post_mode=post_mode,
        published_post_id=published_post_id,
        scheduled_publish_time=scheduled_publish_at.isoformat() if scheduled_publish_at else None,
        response_payload=payload,
    )


def write_publish_log(
    result: PublishResult,
    review: ReviewPackage,
    logs_dir: Path,
    *,
    written_at: datetime | None = None,
) -> Path:
    """Persist a publish attempt result for auditability."""

    current_time = written_at or datetime.now(UTC)
    payload = asdict(result)
    payload["run_date"] = review.run_date.isoformat()
    payload["proposed_topic"] = review.proposed_topic
    payload["written_at"] = current_time.replace(microsecond=0).isoformat()
    path = logs_dir / f"{review.run_date.isoformat()}_publish_log.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
