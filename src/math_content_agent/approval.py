"""Manual approval workflow helpers."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .models import ApprovalGateDecision, ApprovalRecord, ReviewPackage

ALLOWED_APPROVAL_STATUSES = {"PENDING_REVIEW", "APPROVED", "REJECTED", "NEEDS_REVISION"}


class ApprovalValidationError(ValueError):
    """Raised when an approval artifact is malformed or unsafe to use."""


def _require_string(value: object, field_name: str) -> str:
    """Require a string field from raw JSON data."""

    if not isinstance(value, str) or not value.strip():
        raise ApprovalValidationError(f"Approval field '{field_name}' must be a non-empty string.")
    return value.strip()


def parse_approval_payload(payload: dict[str, object]) -> ApprovalRecord:
    """Parse and validate a raw approval JSON payload."""

    raw_date = _require_string(payload.get("date"), "date")
    try:
        run_date = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise ApprovalValidationError("Approval field 'date' must be in YYYY-MM-DD format.") from exc

    status = _require_string(payload.get("status"), "status").upper()
    if status not in ALLOWED_APPROVAL_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_APPROVAL_STATUSES))
        raise ApprovalValidationError(f"Approval status must be one of: {allowed}.")

    reviewer = _require_string(payload.get("reviewer"), "reviewer")
    notes = payload.get("notes", "")
    if notes is None:
        notes = ""
    if not isinstance(notes, str):
        raise ApprovalValidationError("Approval field 'notes' must be a string when present.")

    decided_at = payload.get("decided_at")
    if decided_at is not None and not isinstance(decided_at, str):
        raise ApprovalValidationError("Approval field 'decided_at' must be a string when present.")

    return ApprovalRecord(
        run_date=run_date,
        status=status,
        reviewer=reviewer,
        notes=notes.strip(),
        decided_at=decided_at.strip() if isinstance(decided_at, str) else None,
    )


def load_approval(path: Path) -> ApprovalRecord:
    """Load and validate an approval artifact from disk."""

    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ApprovalValidationError("Approval artifact must contain a JSON object.")
    return parse_approval_payload(payload)


def render_approval_template(review: ReviewPackage) -> str:
    """Render a starter approval artifact for human action."""

    payload = {
        "date": review.run_date.isoformat(),
        "status": "PENDING_REVIEW",
        "reviewer": "admin",
        "notes": "",
        "decided_at": None,
        "proposed_topic": review.proposed_topic,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_approval_template(review: ReviewPackage, approval_dir: Path) -> Path:
    """Write a starter approval artifact next to the review outputs."""

    path = approval_dir / f"{review.run_date.isoformat()}_approval.json"
    path.write_text(render_approval_template(review), encoding="utf-8")
    return path


def evaluate_approval(review: ReviewPackage, approval: ApprovalRecord) -> ApprovalGateDecision:
    """Evaluate whether publishing may proceed."""

    if approval.run_date != review.run_date:
        return ApprovalGateDecision(
            can_publish=False,
            final_status=review.status,
            reason="Approval artifact date does not match the review package date.",
            reviewer=approval.reviewer,
            notes=approval.notes,
        )

    if review.status != "PENDING_REVIEW":
        return ApprovalGateDecision(
            can_publish=False,
            final_status=review.status,
            reason="Only review packages in PENDING_REVIEW state can move toward publishing.",
            reviewer=approval.reviewer,
            notes=approval.notes,
        )

    if approval.status != "APPROVED":
        reason_map = {
            "PENDING_REVIEW": "Human approval is still pending.",
            "REJECTED": "Reviewer rejected the draft, so publishing is blocked.",
            "NEEDS_REVISION": "Reviewer requested revision, so publishing is blocked.",
        }
        return ApprovalGateDecision(
            can_publish=False,
            final_status=approval.status,
            reason=reason_map.get(approval.status, "Approval status does not permit publishing."),
            reviewer=approval.reviewer,
            notes=approval.notes,
        )

    return ApprovalGateDecision(
        can_publish=True,
        final_status="APPROVED",
        reason="Explicit human approval is present, so publishing may proceed when a publisher is implemented.",
        reviewer=approval.reviewer,
        notes=approval.notes,
    )
