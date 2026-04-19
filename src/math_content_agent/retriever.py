"""Retrieval normalization and trusted-source filtering."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from .config import load_trusted_sources
from .models import CandidateTopic, EvidenceBundle, EvidenceItem, NewsCandidate, RetrievalDocument


class RetrievalProvider(Protocol):
    """Provider interface for candidate evidence retrieval."""

    def search(self, candidate: CandidateTopic) -> list[RetrievalDocument]:
        """Return raw retrieval documents for a candidate."""


class NewsRetrievalProvider(Protocol):
    """Provider interface for news evidence retrieval."""

    def search_news(self, candidate: NewsCandidate) -> list[RetrievalDocument]:
        """Return raw retrieval documents for a news candidate."""


def _normalize_domain(url: str) -> str:
    """Return the lowercase hostname for a URL."""

    return urlparse(url).netloc.lower()


def _match_allowed_tier(url: str, source_policy: dict[str, object]) -> str | None:
    """Return the matching policy tier if the URL is allowed."""

    hostname = _normalize_domain(url)
    tiers = source_policy.get("tiers", {})
    if not isinstance(tiers, dict):
        return None

    for tier_name, tier_data in tiers.items():
        if not isinstance(tier_data, dict):
            continue
        domains = tier_data.get("domains", [])
        if not isinstance(domains, list):
            continue
        for allowed_domain in domains:
            allowed = str(allowed_domain).lower()
            if hostname == allowed or hostname.endswith(f".{allowed}"):
                return str(tier_name)
    return None


def is_allowed_source(url: str, source_policy: dict[str, object]) -> bool:
    """Return `True` when a URL belongs to an approved source domain."""

    return _match_allowed_tier(url, source_policy) is not None


def normalize_evidence(
    candidate: CandidateTopic,
    raw_documents: list[RetrievalDocument],
    source_policy: dict[str, object],
) -> EvidenceBundle:
    """Filter raw provider results into a normalized evidence bundle."""

    allowed_items: list[EvidenceItem] = []
    rejected_urls: list[str] = []

    for document in raw_documents:
        source_tier = _match_allowed_tier(document.url, source_policy)
        if source_tier is None:
            rejected_urls.append(document.url)
            continue

        confidence_notes = [f"Source matched allowlist tier {source_tier}."]
        if document.published_at:
            confidence_notes.append("Published/page date metadata was captured for later date relevance checks.")
        else:
            confidence_notes.append("No date metadata was supplied by the retriever.")

        allowed_items.append(
            EvidenceItem(
                title=document.title,
                source=document.source_name,
                url=document.url,
                excerpt=document.excerpt,
                source_type=document.source_type,
                source_tier=source_tier,
                published_at=document.published_at,
                content_mode="STANDARD_MATH_MODE",
                candidate_slug=candidate.slug,
                candidate_title=candidate.title,
                confidence_notes=confidence_notes,
            )
        )

    return EvidenceBundle(
        content_mode="STANDARD_MATH_MODE",
        candidate_slug=candidate.slug,
        candidate_title=candidate.title,
        generated_at=datetime.now(UTC),
        allowed_items=allowed_items,
        rejected_urls=rejected_urls,
    )


def normalize_news_evidence(
    candidate: NewsCandidate,
    raw_documents: list[RetrievalDocument],
    source_policy: dict[str, object],
) -> EvidenceBundle:
    """Filter raw provider results into a normalized news evidence bundle."""

    allowed_items: list[EvidenceItem] = []
    rejected_urls: list[str] = []

    for document in raw_documents:
        source_tier = _match_allowed_tier(document.url, source_policy)
        if source_tier is None:
            rejected_urls.append(document.url)
            continue

        confidence_notes = [f"Source matched allowlist tier {source_tier}."]
        if document.published_at:
            confidence_notes.append("Published/page date metadata was captured for later news recency checks.")
        else:
            confidence_notes.append("No date metadata was supplied by the retriever.")

        allowed_items.append(
            EvidenceItem(
                title=document.title,
                source=document.source_name,
                url=document.url,
                excerpt=document.excerpt,
                source_type=document.source_type,
                source_tier=source_tier,
                published_at=document.published_at,
                content_mode="NEWS_MODE",
                candidate_slug=candidate.slug,
                candidate_title=candidate.title,
                confidence_notes=confidence_notes,
            )
        )

    return EvidenceBundle(
        content_mode="NEWS_MODE",
        candidate_slug=candidate.slug,
        candidate_title=candidate.title,
        generated_at=datetime.now(UTC),
        allowed_items=allowed_items,
        rejected_urls=rejected_urls,
    )


def retrieve_candidate_evidence(
    candidate: CandidateTopic,
    provider: RetrievalProvider,
    source_policy: dict[str, object] | None = None,
) -> EvidenceBundle:
    """Retrieve and normalize evidence for a single candidate."""

    policy = source_policy or load_trusted_sources()
    raw_documents = provider.search(candidate)
    return normalize_evidence(candidate, raw_documents, policy)


def retrieve_news_evidence(
    candidate: NewsCandidate,
    provider: NewsRetrievalProvider,
    source_policy: dict[str, object] | None = None,
) -> EvidenceBundle:
    """Retrieve and normalize evidence for a news candidate."""

    policy = source_policy or load_trusted_sources()
    raw_documents = provider.search_news(candidate)
    return normalize_news_evidence(candidate, raw_documents, policy)


def write_raw_evidence_bundle(bundle: EvidenceBundle, output_dir: Path, output_date: datetime | None = None) -> Path:
    """Persist raw normalized evidence for auditing."""

    payload = {
        "content_mode": bundle.content_mode,
        "candidate_slug": bundle.candidate_slug,
        "candidate_title": bundle.candidate_title,
        "generated_at": bundle.generated_at.replace(microsecond=0).isoformat(),
        "allowed_items": [asdict(item) for item in bundle.allowed_items],
        "rejected_urls": bundle.rejected_urls,
    }
    file_date = (output_date or bundle.generated_at).date().isoformat()
    path = output_dir / f"{file_date}_{bundle.candidate_slug}_evidence.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
