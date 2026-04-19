"""End-to-end orchestration for generation and publish steps."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from .approval import evaluate_approval, load_approval, write_approval_template
from .config import ensure_runtime_dirs, load_settings, load_trusted_sources
from .models import PublishResult, RetrievalDocument, ReviewPackage
from .news import EmptyNewsProvider, NewsProvider, build_daily_selection_plan, write_news_debug
from .package_builder import (
    apply_approval_to_review,
    build_review_package,
    load_review_package,
    write_review_package,
)
from .planner import write_planner_debug
from .publisher_facebook import FacebookGraphApiTransport, publish_review_package, write_publish_log
from .retriever import (
    NewsRetrievalProvider,
    RetrievalProvider,
    retrieve_candidate_evidence,
    retrieve_news_evidence,
    write_raw_evidence_bundle,
)
from .runtime import evaluate_run_day
from .verifier import verify_news_candidate, verify_standard_topic
from .writer import write_news_post, write_standard_topic_post


def _duplicate_notes_from_candidate(candidate) -> list[str]:
    """Extract duplicate-history notes from candidate reasons for reviewer visibility."""

    duplicate_prefixes = ("Potential repeat:", "Theme repeat note:")
    return [reason for reason in getattr(candidate, "reasons", []) if reason.startswith(duplicate_prefixes)]


@dataclass(frozen=True)
class GenerationRunArtifacts:
    """Artifacts created by a weekday generation run."""

    should_run: bool
    mode: str | None
    review: ReviewPackage | None
    review_markdown_path: Path | None
    review_json_path: Path | None
    approval_template_path: Path | None
    evidence_bundle_path: Path | None
    news_debug_path: Path | None
    planner_debug_path: Path | None
    reason: str


@dataclass(frozen=True)
class PublishRunArtifacts:
    """Artifacts created by an approval + publish run."""

    review_json_path: Path
    review_markdown_path: Path
    approval_path: Path
    publish_log_path: Path
    publish_result: PublishResult


class StaticTopicRetrievalProvider:
    """Curated local evidence for standard topic mode."""

    _documents: dict[str, list[RetrievalDocument]] = {
        "gauss-number-theory-turning-point": [
            RetrievalDocument(
                title="Carl Friedrich Gauss",
                url="https://mathshistory.st-andrews.ac.uk/Biographies/Gauss/",
                excerpt="Historical source describing Gauss and his foundational work in number theory in 1801.",
                source_name="MacTutor",
                published_at="2024-01-01",
                source_type="reference",
            ),
            RetrievalDocument(
                title="Gauss and Disquisitiones Arithmeticae",
                url="https://www.ams.org/publicoutreach/math-history/gauss",
                excerpt="AMS notes that Gauss helped reshape number theory, with 1801 often cited as a turning point.",
                source_name="AMS",
                published_at="2024-01-02",
                source_type="reference",
            ),
        ],
        "ramanujan-pattern-insight": [
            RetrievalDocument(
                title="Srinivasa Ramanujan",
                url="https://mathshistory.st-andrews.ac.uk/Biographies/Ramanujan/",
                excerpt="Historical source describing Ramanujan's extraordinary ability to detect deep numerical patterns.",
                source_name="MacTutor",
                published_at="2024-01-01",
                source_type="reference",
            ),
            RetrievalDocument(
                title="Ramanujan's Mathematical Legacy",
                url="https://www.ams.org/publicoutreach/math-history/ramanujan",
                excerpt="AMS highlights Ramanujan's originality and pattern-based insights in number theory.",
                source_name="AMS",
                published_at="2024-01-02",
                source_type="reference",
            ),
        ],
        "noether-symmetry-impact": [
            RetrievalDocument(
                title="Emmy Noether",
                url="https://mathshistory.st-andrews.ac.uk/Biographies/Noether_Emmy/",
                excerpt="Historical source describing Noether's role in abstract algebra and the mathematics of symmetry.",
                source_name="MacTutor",
                published_at="2024-01-01",
                source_type="reference",
            ),
            RetrievalDocument(
                title="Emmy Noether and Symmetry",
                url="https://www.ams.org/publicoutreach/math-history/noether",
                excerpt="AMS explains why Noether's work on symmetry changed modern mathematics and science.",
                source_name="AMS",
                published_at="2024-01-02",
                source_type="reference",
            ),
        ],
        "euclid-axiomatic-proof": [
            RetrievalDocument(
                title="Euclid of Alexandria",
                url="https://mathshistory.st-andrews.ac.uk/Biographies/Euclid/",
                excerpt="Historical source describing Euclid's role in systematic proof and axiomatic geometry.",
                source_name="MacTutor",
                published_at="2024-01-01",
                source_type="reference",
            ),
            RetrievalDocument(
                title="Euclid and Mathematical Proof",
                url="https://www.ams.org/publicoutreach/math-history/euclid",
                excerpt="AMS outlines how Euclid shaped the formal structure of proof in mathematics.",
                source_name="AMS",
                published_at="2024-01-02",
                source_type="reference",
            ),
        ],
        "euler-modern-notation": [
            RetrievalDocument(
                title="Leonhard Euler",
                url="https://mathshistory.st-andrews.ac.uk/Biographies/Euler/",
                excerpt="Historical source describing Euler's influence on modern mathematical notation and analysis.",
                source_name="MacTutor",
                published_at="2024-01-01",
                source_type="reference",
            ),
            RetrievalDocument(
                title="Euler's Notational Legacy",
                url="https://www.ams.org/publicoutreach/math-history/euler",
                excerpt="AMS explains how Euler helped standardize symbols still used in mathematics today.",
                source_name="AMS",
                published_at="2024-01-02",
                source_type="reference",
            ),
        ],
    }

    def search(self, candidate) -> list[RetrievalDocument]:
        return list(self._documents.get(candidate.slug, []))


class StaticNewsRetrievalProvider:
    """Curated local evidence for selected news items."""

    _documents: dict[str, list[RetrievalDocument]] = {
        "telescope-orbital-model": [
            RetrievalDocument(
                title="Orbital model update",
                url="https://www.siam.org/news/orbital-model",
                excerpt="SIAM reported a clearer orbital model in 2026 using updated mathematical analysis.",
                source_name="SIAM",
                published_at="2026-04-18",
                source_type="news",
            ),
            RetrievalDocument(
                title="Observatory follow-up",
                url="https://www.ams.org/news/orbital-model-follow-up",
                excerpt="AMS summarized the same 2026 result and its connection to mathematical modeling.",
                source_name="AMS",
                published_at="2026-04-19",
                source_type="news",
            ),
        ]
    }

    def search_news(self, candidate) -> list[RetrievalDocument]:
        return list(self._documents.get(candidate.slug, []))


def generate_daily_review(
    *,
    now: datetime | None = None,
    config_dir: Path | None = None,
    news_provider: NewsProvider | None = None,
    topic_retrieval_provider: RetrievalProvider | None = None,
    news_retrieval_provider: NewsRetrievalProvider | None = None,
) -> GenerationRunArtifacts:
    """Generate the daily review package and approval template."""

    settings = load_settings(config_dir=config_dir)
    ensure_runtime_dirs(settings)
    decision = evaluate_run_day(now=now, config_dir=config_dir)
    if not decision.should_run:
        return GenerationRunArtifacts(
            should_run=False,
            mode=None,
            review=None,
            review_markdown_path=None,
            review_json_path=None,
            approval_template_path=None,
            evidence_bundle_path=None,
            news_debug_path=None,
            planner_debug_path=None,
            reason=decision.reason,
        )

    source_policy = load_trusted_sources(config_dir=config_dir)
    daily_plan = build_daily_selection_plan(
        run_date=decision.run_date,
        weekday_name=decision.weekday_name,
        theme_slug=decision.theme_slug or "general",
        theme_label=decision.theme_label or "General mathematics topic",
        settings=settings,
        source_policy=source_policy,
        provider=news_provider or EmptyNewsProvider(),
        checked_at=decision.evaluated_at,
    )
    news_debug_path = write_news_debug(daily_plan.news_selection, settings.candidate_cache_dir)
    planner_debug_path = None

    if daily_plan.mode == "NEWS_MODE" and daily_plan.news_selection.selected_candidate is not None:
        candidate = daily_plan.news_selection.selected_candidate
        duplicate_notes: list[str] = []
        bundle = retrieve_news_evidence(
            candidate,
            news_retrieval_provider or StaticNewsRetrievalProvider(),
            source_policy=source_policy,
        )
        verification = verify_news_candidate(
            candidate,
            bundle,
            run_date=decision.run_date,
            max_age_days=settings.news_max_age_days,
            confidence_threshold=settings.confidence_threshold,
        )
        draft = write_news_post(candidate, verification, bundle, decision.run_date)
    else:
        planner_run = daily_plan.planner_run
        if planner_run is None or planner_run.selected_candidate is None:
            raise RuntimeError("Planner did not produce a selected candidate on a weekday run.")
        planner_debug_path = write_planner_debug(planner_run, settings.candidate_cache_dir, decision.evaluated_at)
        candidate = planner_run.selected_candidate
        duplicate_notes = _duplicate_notes_from_candidate(candidate)
        bundle = retrieve_candidate_evidence(
            candidate,
            topic_retrieval_provider or StaticTopicRetrievalProvider(),
            source_policy=source_policy,
        )
        verification = verify_standard_topic(
            candidate,
            bundle,
            confidence_threshold=settings.confidence_threshold,
        )
        draft = write_standard_topic_post(candidate, verification, bundle, decision.run_date, decision.weekday_name)

    evidence_bundle_path = write_raw_evidence_bundle(bundle, settings.raw_evidence_dir, decision.evaluated_at)
    review = build_review_package(
        decision.run_date,
        draft,
        verification,
        bundle,
        duplicate_notes=duplicate_notes,
    )
    review_markdown_path, review_json_path = write_review_package(
        review,
        settings.daily_review_dir,
        settings.verification_json_dir,
    )
    approval_template_path = write_approval_template(review, settings.approval_dir)
    return GenerationRunArtifacts(
        should_run=True,
        mode=review.content_mode,
        review=review,
        review_markdown_path=review_markdown_path,
        review_json_path=review_json_path,
        approval_template_path=approval_template_path,
        evidence_bundle_path=evidence_bundle_path,
        news_debug_path=news_debug_path,
        planner_debug_path=planner_debug_path,
        reason="Daily review package generated successfully.",
    )


def publish_from_approval(
    *,
    run_date: date,
    scheduled_publish_at: datetime | None = None,
    config_dir: Path | None = None,
    post_mode: str | None = None,
    dry_run: bool | None = None,
    page_id: str | None = None,
    access_token: str | None = None,
    transport=None,
) -> PublishRunArtifacts:
    """Load saved artifacts, evaluate approval, and publish or schedule if allowed."""

    settings = load_settings(config_dir=config_dir)
    ensure_runtime_dirs(settings)
    review_json_path = settings.verification_json_dir / f"{run_date.isoformat()}_review.json"
    review_markdown_path = settings.daily_review_dir / f"{run_date.isoformat()}_review.md"
    approval_path = settings.approval_dir / f"{run_date.isoformat()}_approval.json"

    review = load_review_package(review_json_path)
    approval_record = load_approval(approval_path)
    gate_decision = evaluate_approval(review, approval_record)

    if approval_record.run_date == review.run_date:
        updated_review = apply_approval_to_review(review, approval_record)
    else:
        updated_review = review

    effective_page_id = page_id or os.environ.get("FACEBOOK_PAGE_ID")
    effective_access_token = access_token or os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
    publish_result = publish_review_package(
        updated_review,
        gate_decision,
        post_mode=post_mode or settings.post_mode,
        dry_run=settings.facebook_dry_run if dry_run is None else dry_run,
        page_id=effective_page_id,
        access_token=effective_access_token,
        transport=transport or FacebookGraphApiTransport(),
        scheduled_publish_at=scheduled_publish_at,
    )

    updated_notes = list(updated_review.verification_notes)
    updated_notes.append(publish_result.reason)
    final_review = ReviewPackage(
        run_date=updated_review.run_date,
        content_mode=updated_review.content_mode,
        proposed_topic=updated_review.proposed_topic,
        date_relevance_type=updated_review.date_relevance_type,
        why_relevant=updated_review.why_relevant,
        thai_draft=updated_review.thai_draft,
        fact_summary=updated_review.fact_summary,
        short_references=updated_review.short_references,
        full_references=updated_review.full_references,
        duplicate_notes=updated_review.duplicate_notes,
        verification_notes=updated_notes,
        confidence=updated_review.confidence,
        status=publish_result.status if gate_decision.can_publish else updated_review.status,
    )
    write_review_package(final_review, settings.daily_review_dir, settings.verification_json_dir)
    publish_log_path = write_publish_log(publish_result, final_review, settings.logs_dir)
    return PublishRunArtifacts(
        review_json_path=review_json_path,
        review_markdown_path=review_markdown_path,
        approval_path=approval_path,
        publish_log_path=publish_log_path,
        publish_result=publish_result,
    )
