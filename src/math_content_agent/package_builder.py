"""Review package generation for markdown and JSON outputs."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path

from .models import ApprovalRecord, DraftPost, EvidenceBundle, ReviewPackage, VerificationResult


def _status_from_verification(verification: VerificationResult) -> str:
    """Map verification state to a review status."""

    return "PENDING_REVIEW" if verification.publishable else "BLOCKED_LOW_CONFIDENCE"


def _short_references(bundle: EvidenceBundle) -> list[str]:
    """Return compact references for the reviewer."""

    return [f"{item.source} - {item.title}" for item in bundle.allowed_items]


def _full_references(bundle: EvidenceBundle) -> list[str]:
    """Return full references for auditability."""

    references: list[str] = []
    for item in bundle.allowed_items:
        published = f" ({item.published_at[:10]})" if item.published_at else ""
        references.append(f"{item.source}. {item.title}{published}. {item.url}")
    return references


def build_review_package(
    run_date: date,
    draft: DraftPost,
    verification: VerificationResult,
    bundle: EvidenceBundle,
    *,
    duplicate_notes: list[str] | None = None,
) -> ReviewPackage:
    """Build a structured review package."""

    return ReviewPackage(
        run_date=run_date,
        content_mode=draft.content_mode,
        proposed_topic=draft.topic_title,
        date_relevance_type=verification.date_link_type,
        why_relevant=draft.why_relevant,
        thai_draft=draft.body + ("\n\n" + " ".join(draft.hashtags) if draft.hashtags else ""),
        fact_summary=draft.fact_summary,
        short_references=_short_references(bundle),
        full_references=_full_references(bundle),
        duplicate_notes=list(duplicate_notes or []),
        verification_notes=[*verification.verification_notes, *verification.conflicts, verification.reason],
        confidence=verification.confidence,
        status=_status_from_verification(verification),
    )


def render_review_markdown(review: ReviewPackage) -> str:
    """Render the human-readable markdown package."""

    fact_summary = "\n".join(f"- {item}" for item in review.fact_summary) or "- ไม่มี"
    short_refs = "\n".join(f"{index}. {item}" for index, item in enumerate(review.short_references, start=1)) or "1. ไม่มี"
    full_refs = "\n".join(f"{index}. {item}" for index, item in enumerate(review.full_references, start=1)) or "1. ไม่มี"
    duplicate_notes = (
        "\n".join(f"- {item}" for item in review.duplicate_notes)
        if review.duplicate_notes
        else "- No recent duplicate match found."
    )
    verification_notes = (
        "\n".join(f"- {item}" for item in review.verification_notes)
        if review.verification_notes
        else "- ไม่มี"
    )
    return f"""# Daily Math Post Draft - {review.run_date.isoformat()}

## Proposed Topic
{review.proposed_topic}

## Date Relevance Type
{review.date_relevance_type}

## Why this matches today
{review.why_relevant}

## Draft Facebook Post
{review.thai_draft}

## Fact Summary
{fact_summary}

## Short References
{short_refs}

## Full References
{full_refs}

## Duplicate Check
{duplicate_notes}

## Verification Notes
{verification_notes}

## Confidence
{review.confidence:.2f}

## Status
{review.status}
"""


def render_review_json(review: ReviewPackage) -> str:
    """Render the machine-readable JSON package."""

    payload = asdict(review)
    payload["run_date"] = review.run_date.isoformat()
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_review_package(
    review: ReviewPackage,
    markdown_dir: Path,
    json_dir: Path,
) -> tuple[Path, Path]:
    """Write markdown and JSON review artifacts to disk."""

    markdown_path = markdown_dir / f"{review.run_date.isoformat()}_review.md"
    json_path = json_dir / f"{review.run_date.isoformat()}_review.json"
    markdown_path.write_text(render_review_markdown(review), encoding="utf-8")
    json_path.write_text(render_review_json(review), encoding="utf-8")
    return markdown_path, json_path


def load_review_package(path: Path) -> ReviewPackage:
    """Load a review package from its JSON artifact."""

    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return ReviewPackage(
        run_date=date.fromisoformat(payload["run_date"]),
        content_mode=payload["content_mode"],
        proposed_topic=payload["proposed_topic"],
        date_relevance_type=payload.get("date_relevance_type", "weekday_theme"),
        why_relevant=payload["why_relevant"],
        thai_draft=payload["thai_draft"],
        fact_summary=list(payload["fact_summary"]),
        short_references=list(payload["short_references"]),
        full_references=list(payload["full_references"]),
        duplicate_notes=list(payload.get("duplicate_notes", [])),
        verification_notes=list(payload["verification_notes"]),
        confidence=float(payload["confidence"]),
        status=payload["status"],
    )


def apply_approval_to_review(review: ReviewPackage, approval: ApprovalRecord) -> ReviewPackage:
    """Return a review package updated with the human approval state."""

    notes = list(review.verification_notes)
    if approval.notes:
        notes.append(f"Reviewer note ({approval.reviewer}): {approval.notes}")
    return replace(review, status=approval.status, verification_notes=notes)
