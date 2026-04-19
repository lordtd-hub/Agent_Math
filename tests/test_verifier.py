"""Tests for verification rules in topic mode and news mode."""

from __future__ import annotations

import unittest
from datetime import UTC, date, datetime

from math_content_agent.models import CandidateTopic, EvidenceBundle, EvidenceItem, NewsCandidate
from math_content_agent.verifier import verify_news_candidate, verify_standard_topic


class VerifierTests(unittest.TestCase):
    def _topic_candidate(self, *, date_link_explanation: str = "Matches Monday history theme.") -> CandidateTopic:
        return CandidateTopic(
            title="Gauss กับจุดเปลี่ยนของทฤษฎีจำนวน",
            slug="gauss-number-theory-turning-point",
            theme_slug="history",
            theme_label="Mathematician birthdays and history",
            angle="historical_profile",
            entity="Carl Friedrich Gauss",
            date_link_type="weekday_theme",
            date_link_explanation=date_link_explanation,
            reasons=["Theme match."],
            base_score=0.7,
            duplicate_penalty=0.0,
            final_score=0.7,
        )

    def _news_candidate(
        self,
        *,
        published_at: str = "2026-04-18",
        relevance: str = "The story depends on mathematical modeling.",
        speculative: bool = False,
        major_claims_clear: bool = True,
    ) -> NewsCandidate:
        return NewsCandidate(
            title="New telescope data sharpens orbital model",
            slug="telescope-orbital-model",
            url="https://www.siam.org/news/orbital-model",
            source_name="SIAM",
            published_at=published_at,
            topic_domain="astronomy",
            summary="Researchers published a clearer orbital model based on fresh observations.",
            math_relevance=relevance,
            source_count=2,
            major_claims_clear=major_claims_clear,
            is_speculative=speculative,
        )

    def _bundle(self, *, mode: str, excerpts: list[str], published_at: str = "2026-04-18") -> EvidenceBundle:
        items = [
            EvidenceItem(
                title=f"Source {index}",
                source=f"Source {index}",
                url=f"https://allowed.example/{mode}/{index}",
                excerpt=excerpt,
                source_type="reference",
                source_tier="tier_1",
                published_at=published_at,
                content_mode=mode,
                candidate_slug="candidate",
                candidate_title="Candidate",
                confidence_notes=[],
            )
            for index, excerpt in enumerate(excerpts, start=1)
        ]
        return EvidenceBundle(
            content_mode=mode,
            candidate_slug="candidate",
            candidate_title="Candidate",
            generated_at=datetime(2026, 4, 20, 2, 0, tzinfo=UTC),
            allowed_items=items,
            rejected_urls=[],
        )

    def test_conflicting_sources_are_blocked(self) -> None:
        result = verify_standard_topic(
            self._topic_candidate(),
            self._bundle(
                mode="STANDARD_MATH_MODE",
                excerpts=[
                    "A historical source says the event happened in 1801.",
                    "Another historical source says the event happened in 1802.",
                ],
            ),
            confidence_threshold=0.75,
        )

        self.assertFalse(result.publishable)
        self.assertTrue(result.conflicts)

    def test_weak_date_linkage_is_blocked(self) -> None:
        result = verify_standard_topic(
            self._topic_candidate(date_link_explanation=""),
            self._bundle(
                mode="STANDARD_MATH_MODE",
                excerpts=[
                    "A source notes the same event in 1801.",
                    "A second source also notes the same event in 1801.",
                ],
            ),
            confidence_threshold=0.75,
        )

        self.assertFalse(result.publishable)
        self.assertEqual(result.fact_checks[0].name, "date_linkage")
        self.assertFalse(result.fact_checks[0].passed)

    def test_unverifiable_quote_is_blocked(self) -> None:
        result = verify_standard_topic(
            self._topic_candidate(),
            self._bundle(
                mode="STANDARD_MATH_MODE",
                excerpts=[
                    "A source notes the same event in 1801.",
                    "A second source also notes the same event in 1801.",
                ],
            ),
            confidence_threshold=0.75,
            requested_quote="Mathematics is the queen of the sciences.",
        )

        quote_check = next(check for check in result.fact_checks if check.name == "quote_verification")
        self.assertFalse(result.publishable)
        self.assertFalse(quote_check.passed)

    def test_high_confidence_valid_standard_case(self) -> None:
        result = verify_standard_topic(
            self._topic_candidate(),
            self._bundle(
                mode="STANDARD_MATH_MODE",
                excerpts=[
                    'A source notes the same event in 1801 and includes "Verified quote".',
                    'A second source also notes the same event in 1801 and repeats "Verified quote".',
                ],
            ),
            confidence_threshold=0.75,
            requested_quote="Verified quote",
        )

        self.assertTrue(result.publishable)
        self.assertGreaterEqual(result.confidence, 0.75)

    def test_weak_news_recency_is_blocked(self) -> None:
        result = verify_news_candidate(
            self._news_candidate(published_at="2026-04-01"),
            self._bundle(
                mode="NEWS_MODE",
                excerpts=[
                    "A report published in 2026 confirms the observation.",
                    "A second report published in 2026 confirms the observation.",
                ],
            ),
            run_date=date(2026, 4, 20),
            max_age_days=7,
            confidence_threshold=0.75,
        )

        self.assertFalse(result.publishable)
        recency_check = next(check for check in result.fact_checks if check.name == "news_recency")
        self.assertFalse(recency_check.passed)

    def test_speculative_news_is_blocked(self) -> None:
        result = verify_news_candidate(
            self._news_candidate(speculative=True),
            self._bundle(
                mode="NEWS_MODE",
                excerpts=[
                    "A report published in 2026 confirms the observation.",
                    "A second report published in 2026 confirms the observation.",
                ],
            ),
            run_date=date(2026, 4, 20),
            max_age_days=7,
            confidence_threshold=0.75,
        )

        self.assertFalse(result.publishable)
        speculative_check = next(check for check in result.fact_checks if check.name == "speculative_screen")
        self.assertFalse(speculative_check.passed)

    def test_valid_news_case(self) -> None:
        result = verify_news_candidate(
            self._news_candidate(),
            self._bundle(
                mode="NEWS_MODE",
                excerpts=[
                    'A report published in 2026 confirms the observation and includes "Verified quote".',
                    'A second report published in 2026 confirms the observation and repeats "Verified quote".',
                ],
            ),
            run_date=date(2026, 4, 20),
            max_age_days=7,
            confidence_threshold=0.75,
            requested_quote="Verified quote",
        )

        self.assertTrue(result.publishable)
        self.assertEqual(result.content_mode, "NEWS_MODE")


if __name__ == "__main__":
    unittest.main()
