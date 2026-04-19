"""Typed models shared across the MVP foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    """Application settings loaded from config files and environment overrides."""

    timezone: str
    output_language: str
    post_mode: str
    facebook_dry_run: bool
    confidence_threshold: float
    weekday_schedule_enabled: bool
    news_enabled: bool
    news_max_age_days: int
    news_min_sources: int
    news_require_multi_source_for_major_claims: bool
    daily_review_dir: Path
    verification_json_dir: Path
    approval_dir: Path
    raw_evidence_dir: Path
    logs_dir: Path
    planner_candidate_target: int
    post_history_path: Path
    candidate_cache_dir: Path
    recent_history_window_days: int
    duplicate_topic_penalty: float
    duplicate_entity_penalty: float
    duplicate_theme_penalty: float


@dataclass(frozen=True)
class SchedulerDecision:
    """Result of evaluating whether a run should continue today."""

    should_run: bool
    run_date: date
    weekday_name: str
    evaluated_at: datetime
    reason: str
    theme_slug: str | None = None
    theme_label: str | None = None


@dataclass(frozen=True)
class CandidateTopic:
    """Planner candidate before retrieval and verification."""

    title: str
    slug: str
    theme_slug: str
    theme_label: str
    angle: str
    entity: str | None
    date_link_type: str
    date_link_explanation: str
    reasons: list[str] = field(default_factory=list)
    base_score: float = 0.0
    duplicate_penalty: float = 0.0
    final_score: float = 0.0
    requires_retrieval: bool = True


@dataclass(frozen=True)
class PlannerRun:
    """Output of a single planner execution."""

    run_date: date
    weekday_name: str
    theme_slug: str
    theme_label: str
    output_language: str
    candidates: list[CandidateTopic]
    selected_candidate: CandidateTopic | None


@dataclass(frozen=True)
class RetrievalDocument:
    """Raw provider result before source policy filtering."""

    title: str
    url: str
    excerpt: str
    source_name: str
    published_at: str | None
    source_type: str


@dataclass(frozen=True)
class EvidenceItem:
    """Normalized evidence record used by later verification steps."""

    title: str
    source: str
    url: str
    excerpt: str
    source_type: str
    source_tier: str
    published_at: str | None
    content_mode: str
    candidate_slug: str
    candidate_title: str
    confidence_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceBundle:
    """Evidence bundle attached to one candidate topic."""

    content_mode: str
    candidate_slug: str
    candidate_title: str
    generated_at: datetime
    allowed_items: list[EvidenceItem]
    rejected_urls: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NewsCandidate:
    """Candidate news item considered before topic fallback."""

    title: str
    slug: str
    url: str
    source_name: str
    published_at: str
    topic_domain: str
    summary: str
    math_relevance: str
    source_count: int = 1
    major_claims_clear: bool = True
    is_speculative: bool = False


@dataclass(frozen=True)
class NewsSelectionResult:
    """Outcome of evaluating current news candidates."""

    checked_at: datetime
    mode: str
    reasons: list[str]
    candidates_considered: list[NewsCandidate]
    valid_candidates: list[NewsCandidate]
    selected_candidate: NewsCandidate | None


@dataclass(frozen=True)
class DailySelectionPlan:
    """Top-level content decision for the day."""

    mode: str
    run_date: date
    weekday_name: str
    output_language: str
    reasons: list[str]
    news_selection: NewsSelectionResult
    planner_run: PlannerRun | None = None


@dataclass(frozen=True)
class FactCheckResult:
    """Single verification check outcome."""

    name: str
    passed: bool
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerificationResult:
    """Structured verifier output shared by later pipeline stages."""

    content_mode: str
    publishable: bool
    confidence: float
    topic_title: str
    date_link_type: str
    fact_checks: list[FactCheckResult]
    conflicts: list[str]
    verification_notes: list[str]
    required_human_review: bool
    reason: str


@dataclass(frozen=True)
class DraftPost:
    """Thai draft content prepared for human review."""

    content_mode: str
    topic_title: str
    why_relevant: str
    body: str
    fact_summary: list[str]
    hashtags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewPackage:
    """Combined human-readable and machine-readable review data."""

    run_date: date
    content_mode: str
    proposed_topic: str
    date_relevance_type: str
    why_relevant: str
    thai_draft: str
    fact_summary: list[str]
    short_references: list[str]
    full_references: list[str]
    duplicate_notes: list[str]
    verification_notes: list[str]
    confidence: float
    status: str


@dataclass(frozen=True)
class ApprovalRecord:
    """Human review decision loaded from an approval artifact."""

    run_date: date
    status: str
    reviewer: str
    notes: str = ""
    decided_at: str | None = None


@dataclass(frozen=True)
class ApprovalGateDecision:
    """Decision returned by the approval gate."""

    can_publish: bool
    final_status: str
    reason: str
    reviewer: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class PublishResult:
    """Outcome of a publishing attempt or dry-run."""

    attempted: bool
    status: str
    reason: str
    content_mode: str
    post_mode: str
    published_post_id: str | None = None
    scheduled_publish_time: str | None = None
    response_payload: dict[str, object] | None = None
    error_message: str | None = None
