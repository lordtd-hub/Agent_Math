"""Verification engine for standard topic mode and news mode."""

from __future__ import annotations

import re
from datetime import date

from .models import (
    CandidateTopic,
    EvidenceBundle,
    FactCheckResult,
    NewsCandidate,
    VerificationResult,
)

YEAR_PATTERN = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")


def _extract_years(bundle: EvidenceBundle) -> set[str]:
    """Collect explicit years from evidence excerpts and metadata."""

    years: set[str] = set()
    for item in bundle.allowed_items:
        for match in YEAR_PATTERN.findall(item.excerpt):
            years.add(match)
    return years


def _check_source_count(bundle: EvidenceBundle, minimum: int) -> FactCheckResult:
    """Check whether enough approved sources were retained."""

    unique_urls = {item.url for item in bundle.allowed_items}
    passed = len(unique_urls) >= minimum
    notes = [f"Found {len(unique_urls)} approved sources; expected at least {minimum}."]
    return FactCheckResult(name="source_count", passed=passed, notes=notes)


def _check_conflicts(bundle: EvidenceBundle) -> tuple[FactCheckResult, list[str]]:
    """Detect obvious year conflicts across approved sources."""

    years = _extract_years(bundle)
    if len(years) > 1:
        conflicts = [f"Evidence contains conflicting year references: {', '.join(sorted(years))}."]
        return (
            FactCheckResult(
                name="conflict_detection",
                passed=False,
                notes=["Multiple different years were found across approved evidence excerpts."],
            ),
            conflicts,
        )
    return (
        FactCheckResult(
            name="conflict_detection",
            passed=True,
            notes=["No obvious conflicting year references were detected in approved evidence."],
        ),
        [],
    )


def _check_quote_verification(bundle: EvidenceBundle, requested_quote: str | None) -> FactCheckResult:
    """Require exact quote presence in at least one approved source when requested."""

    if not requested_quote:
        return FactCheckResult(name="quote_verification", passed=True, notes=["No quote was requested for use."])

    quote_matches = sum(1 for item in bundle.allowed_items if requested_quote in item.excerpt)
    passed = quote_matches >= 1
    notes = [f"Exact quote match count in approved evidence: {quote_matches}."]
    if not passed:
        notes.append("Requested quote could not be verified and must not be used.")
    return FactCheckResult(name="quote_verification", passed=passed, notes=notes)


def _score_confidence(checks: list[FactCheckResult], conflicts: list[str]) -> float:
    """Compute a conservative confidence score from boolean checks."""

    if not checks:
        return 0.0
    passed_ratio = sum(1 for check in checks if check.passed) / len(checks)
    score = 0.45 + (0.45 * passed_ratio)
    if conflicts:
        score -= 0.25
    return max(0.0, min(1.0, round(score, 2)))


def verify_standard_topic(
    candidate: CandidateTopic,
    bundle: EvidenceBundle,
    confidence_threshold: float,
    requested_quote: str | None = None,
) -> VerificationResult:
    """Verify a standard math-topic candidate."""

    date_link_passed = bool(candidate.date_link_type and candidate.date_link_explanation.strip())
    date_link_check = FactCheckResult(
        name="date_linkage",
        passed=date_link_passed,
        notes=[
            candidate.date_link_explanation if date_link_passed else "Candidate did not provide explicit date linkage."
        ],
    )
    source_check = _check_source_count(bundle, minimum=2)
    conflict_check, conflicts = _check_conflicts(bundle)
    quote_check = _check_quote_verification(bundle, requested_quote)

    checks = [date_link_check, source_check, conflict_check, quote_check]
    confidence = _score_confidence(checks, conflicts)
    publishable = all(check.passed for check in checks) and confidence >= confidence_threshold and not conflicts
    notes = [
        "Standard math topic verification requires explicit date linkage and multiple reliable sources.",
        f"Confidence threshold for publishability is {confidence_threshold:.2f}.",
    ]
    if candidate.date_link_type == "weekday_theme":
        notes.append("This topic is currently linked by weekday theme, not by an exact anniversary or exact historical date.")
    elif candidate.date_link_type == "exact_date_link":
        notes.append("This topic includes an exact date linkage that should be reflected clearly in the final wording.")
    reason = (
        "Standard topic passed baseline verification checks."
        if publishable
        else "Standard topic did not satisfy date linkage, source, quote, or conflict requirements."
    )
    return VerificationResult(
        content_mode="STANDARD_MATH_MODE",
        publishable=publishable,
        confidence=confidence,
        topic_title=candidate.title,
        date_link_type=candidate.date_link_type,
        fact_checks=checks,
        conflicts=conflicts,
        verification_notes=notes,
        required_human_review=True,
        reason=reason,
    )


def verify_news_candidate(
    candidate: NewsCandidate,
    bundle: EvidenceBundle,
    run_date: date,
    max_age_days: int,
    confidence_threshold: float,
    requested_quote: str | None = None,
) -> VerificationResult:
    """Verify a news candidate according to strict recency and clarity rules."""

    try:
        published_date = date.fromisoformat(candidate.published_at[:10])
        age_in_days = (run_date - published_date).days
        recency_passed = 0 <= age_in_days <= max_age_days
    except ValueError:
        age_in_days = None
        recency_passed = False

    recency_check = FactCheckResult(
        name="news_recency",
        passed=recency_passed,
        notes=[
            (
                f"News item is {age_in_days} days old, within the configured {max_age_days}-day window."
                if age_in_days is not None
                else "News publication date could not be parsed."
            )
        ],
    )
    relevance_check = FactCheckResult(
        name="news_relevance",
        passed=bool(candidate.math_relevance.strip()),
        notes=[candidate.math_relevance or "News item did not include an explicit mathematics/scientific reasoning link."],
    )
    speculative_check = FactCheckResult(
        name="speculative_screen",
        passed=not candidate.is_speculative and candidate.major_claims_clear,
        notes=[
            "News item is non-speculative and its major claims are clear."
            if (not candidate.is_speculative and candidate.major_claims_clear)
            else "News item was speculative or its major claims were unclear."
        ],
    )
    source_check = _check_source_count(bundle, minimum=2)
    conflict_check, conflicts = _check_conflicts(bundle)
    quote_check = _check_quote_verification(bundle, requested_quote)

    checks = [recency_check, relevance_check, speculative_check, source_check, conflict_check, quote_check]
    confidence = _score_confidence(checks, conflicts)
    publishable = all(check.passed for check in checks) and confidence >= confidence_threshold and not conflicts
    notes = [
        "News verification requires explicit recency, trusted sourcing, and a clear connection to mathematics or scientific reasoning.",
        f"Confidence threshold for publishability is {confidence_threshold:.2f}.",
    ]
    reason = (
        "News item passed baseline verification checks."
        if publishable
        else "News item failed recency, relevance, speculative, source, quote, or conflict requirements."
    )
    return VerificationResult(
        content_mode="NEWS_MODE",
        publishable=publishable,
        confidence=confidence,
        topic_title=candidate.title,
        date_link_type="news_recency",
        fact_checks=checks,
        conflicts=conflicts,
        verification_notes=notes,
        required_human_review=True,
        reason=reason,
    )
