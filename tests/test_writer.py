"""Tests for Thai post drafting."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from math_content_agent.models import CandidateTopic, EvidenceBundle, EvidenceItem, NewsCandidate, VerificationResult
from math_content_agent.writer import write_news_post, write_standard_topic_post


class WriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.standard_candidate = CandidateTopic(
            title="Gauss กับจุดเปลี่ยนของทฤษฎีจำนวน",
            slug="gauss-number-theory-turning-point",
            theme_slug="history",
            theme_label="Mathematician birthdays and history",
            angle="historical_profile",
            entity="Carl Friedrich Gauss",
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
            summary="นักวิจัยรายงานข้อมูลใหม่ที่ช่วยให้แบบจำลองวงโคจรแม่นยำขึ้น",
            math_relevance="ข่าวนี้อาศัยแบบจำลองเชิงคณิตศาสตร์และการวิเคราะห์เชิงตัวเลข",
            source_count=2,
            major_claims_clear=True,
            is_speculative=False,
        )
        self.standard_bundle = EvidenceBundle(
            content_mode="STANDARD_MATH_MODE",
            candidate_slug="gauss-number-theory-turning-point",
            candidate_title=self.standard_candidate.title,
            generated_at=datetime(2026, 4, 20, 2, 0, tzinfo=UTC),
            allowed_items=[
                EvidenceItem(
                    title="Gauss biography",
                    source="AMS",
                    url="https://www.ams.org/gauss",
                    excerpt="Historical source describing Gauss and number theory.",
                    source_type="reference",
                    source_tier="tier_1",
                    published_at="2024-01-01",
                    content_mode="STANDARD_MATH_MODE",
                    candidate_slug="gauss-number-theory-turning-point",
                    candidate_title=self.standard_candidate.title,
                    confidence_notes=[],
                ),
                EvidenceItem(
                    title="Gauss archive",
                    source="Mactutor",
                    url="https://mathshistory.st-andrews.ac.uk/Gauss/",
                    excerpt="Second historical source describing the same theme.",
                    source_type="reference",
                    source_tier="tier_2",
                    published_at="2024-01-02",
                    content_mode="STANDARD_MATH_MODE",
                    candidate_slug="gauss-number-theory-turning-point",
                    candidate_title=self.standard_candidate.title,
                    confidence_notes=[],
                ),
            ],
            rejected_urls=[],
        )
        self.news_bundle = EvidenceBundle(
            content_mode="NEWS_MODE",
            candidate_slug="telescope-orbital-model",
            candidate_title=self.news_candidate.title,
            generated_at=datetime(2026, 4, 20, 2, 0, tzinfo=UTC),
            allowed_items=[
                EvidenceItem(
                    title="Orbital model update",
                    source="SIAM",
                    url="https://www.siam.org/news/orbital-model",
                    excerpt="A report on a sharper orbital model.",
                    source_type="news",
                    source_tier="tier_1",
                    published_at="2026-04-18",
                    content_mode="NEWS_MODE",
                    candidate_slug="telescope-orbital-model",
                    candidate_title=self.news_candidate.title,
                    confidence_notes=[],
                ),
                EvidenceItem(
                    title="Observatory follow-up",
                    source="AMS",
                    url="https://www.ams.org/news/orbital-model-follow-up",
                    excerpt="A second report confirms the same result.",
                    source_type="news",
                    source_tier="tier_1",
                    published_at="2026-04-19",
                    content_mode="NEWS_MODE",
                    candidate_slug="telescope-orbital-model",
                    candidate_title=self.news_candidate.title,
                    confidence_notes=[],
                ),
            ],
            rejected_urls=[],
        )
        self.standard_verification = VerificationResult(
            content_mode="STANDARD_MATH_MODE",
            publishable=True,
            confidence=0.90,
            topic_title=self.standard_candidate.title,
            date_link_type="weekday_theme",
            fact_checks=[],
            conflicts=[],
            verification_notes=["Standard topic verification passed."],
            required_human_review=True,
            reason="OK",
        )
        self.news_verification = VerificationResult(
            content_mode="NEWS_MODE",
            publishable=True,
            confidence=0.88,
            topic_title=self.news_candidate.title,
            date_link_type="news_recency",
            fact_checks=[],
            conflicts=[],
            verification_notes=["News verification passed."],
            required_human_review=True,
            reason="OK",
        )

    def test_standard_writer_generates_thai_post(self) -> None:
        draft = write_standard_topic_post(
            self.standard_candidate,
            self.standard_verification,
            self.standard_bundle,
            datetime(2026, 4, 20).date(),
            "Monday",
        )

        self.assertEqual(draft.content_mode, "STANDARD_MATH_MODE")
        self.assertIn("วันนี้ภาควิชาคณิตศาสตร์ชวนมองเรื่อง", draft.body)
        self.assertIn(self.standard_candidate.title, draft.body)
        self.assertIn("วันที่ 2026-04-20", draft.why_relevant)
        self.assertIn("ธีมของวันจันทร์", draft.why_relevant)
        self.assertEqual(draft.hashtags, ["#คณิต(วิทย์)มรส.", "#MathSCISRU"])
        self.assertTrue(draft.fact_summary)

    def test_news_writer_generates_thai_news_post(self) -> None:
        draft = write_news_post(
            self.news_candidate,
            self.news_verification,
            self.news_bundle,
            datetime(2026, 4, 20).date(),
        )

        self.assertEqual(draft.content_mode, "NEWS_MODE")
        self.assertIn("ข่าววิทยาศาสตร์วันนี้", draft.body)
        self.assertIn(self.news_candidate.math_relevance, draft.body)
        self.assertIn("2026-04-18", draft.why_relevant)
        self.assertEqual(draft.hashtags, ["#คณิต(วิทย์)มรส.", "#MathSCISRU"])
        self.assertTrue(draft.fact_summary)


if __name__ == "__main__":
    unittest.main()
