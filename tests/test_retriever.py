"""Tests for trusted-source filtering and evidence storage."""

from __future__ import annotations

import json
import unittest
from datetime import date

from math_content_agent.config import ensure_runtime_dirs, load_settings, load_trusted_sources
from math_content_agent.models import CandidateTopic, NewsCandidate, RetrievalDocument
from math_content_agent.retriever import (
    is_allowed_source,
    normalize_evidence,
    normalize_news_evidence,
    write_raw_evidence_bundle,
)


class RetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_trusted_sources()
        self.settings = load_settings(env={})
        self.candidate = CandidateTopic(
            title="Euler กับภาษาสัญลักษณ์ของคณิตศาสตร์สมัยใหม่",
            slug="euler-modern-notation",
            theme_slug="history",
            theme_label="Mathematician birthdays and history",
            angle="historical_profile",
            entity="Leonhard Euler",
            date_link_type="weekday_theme",
            date_link_explanation="Matches Monday history theme.",
            reasons=["Theme match."],
            base_score=0.7,
            duplicate_penalty=0.0,
            final_score=0.7,
        )
        self.news_candidate = NewsCandidate(
            title="New telescope data sharpens orbital model",
            slug="telescope-orbital-model",
            url="https://www.siam.org/news/orbital-model",
            source_name="SIAM",
            published_at="2026-04-18",
            topic_domain="astronomy",
            summary="Researchers published a clearer orbital model based on fresh observations.",
            math_relevance="The story depends on mathematical modeling and numerical analysis.",
            source_count=2,
            major_claims_clear=True,
            is_speculative=False,
        )

    def test_allowlist_accepts_known_domain(self) -> None:
        self.assertTrue(is_allowed_source("https://mathworld.wolfram.com/Euler.html", self.policy))

    def test_allowlist_rejects_unknown_domain(self) -> None:
        self.assertFalse(is_allowed_source("https://random-math-blog.example/euler", self.policy))

    def test_normalize_evidence_filters_unapproved_sources(self) -> None:
        bundle = normalize_evidence(
            self.candidate,
            [
                RetrievalDocument(
                    title="Euler",
                    url="https://mathworld.wolfram.com/Euler.html",
                    excerpt="Reference excerpt",
                    source_name="MathWorld",
                    published_at="2024-01-01",
                    source_type="reference",
                ),
                RetrievalDocument(
                    title="Euler blog post",
                    url="https://random-math-blog.example/euler",
                    excerpt="Untrusted excerpt",
                    source_name="Random Blog",
                    published_at=None,
                    source_type="blog",
                ),
            ],
            self.policy,
        )

        self.assertEqual(len(bundle.allowed_items), 1)
        self.assertEqual(bundle.content_mode, "STANDARD_MATH_MODE")
        self.assertEqual(bundle.allowed_items[0].source_tier, "tier_2")
        self.assertEqual(bundle.rejected_urls, ["https://random-math-blog.example/euler"])

    def test_normalize_news_evidence_filters_unapproved_sources(self) -> None:
        bundle = normalize_news_evidence(
            self.news_candidate,
            [
                RetrievalDocument(
                    title="Orbital model update",
                    url="https://www.siam.org/news/orbital-model",
                    excerpt="Reference excerpt",
                    source_name="SIAM",
                    published_at="2026-04-18",
                    source_type="news",
                ),
                RetrievalDocument(
                    title="Rumor repost",
                    url="https://unknown.example/rumor",
                    excerpt="Untrusted excerpt",
                    source_name="Unknown",
                    published_at="2026-04-18",
                    source_type="news",
                ),
            ],
            self.policy,
        )

        self.assertEqual(bundle.content_mode, "NEWS_MODE")
        self.assertEqual(len(bundle.allowed_items), 1)
        self.assertEqual(bundle.allowed_items[0].content_mode, "NEWS_MODE")
        self.assertEqual(bundle.rejected_urls, ["https://unknown.example/rumor"])

    def test_raw_evidence_bundle_is_written(self) -> None:
        ensure_runtime_dirs(self.settings)
        bundle = normalize_evidence(
            self.candidate,
            [
                RetrievalDocument(
                    title="Euler",
                    url="https://mathworld.wolfram.com/Euler.html",
                    excerpt="Reference excerpt",
                    source_name="MathWorld",
                    published_at="2024-01-01",
                    source_type="reference",
                )
            ],
            self.policy,
        )

        path = write_raw_evidence_bundle(bundle, self.settings.raw_evidence_dir)
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["content_mode"], "STANDARD_MATH_MODE")
        self.assertEqual(payload["candidate_slug"], "euler-modern-notation")
        self.assertEqual(len(payload["allowed_items"]), 1)


if __name__ == "__main__":
    unittest.main()
