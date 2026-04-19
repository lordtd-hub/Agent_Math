"""Thai draft writer for standard topics and news mode."""

from __future__ import annotations

from datetime import date

from .models import CandidateTopic, DraftPost, EvidenceBundle, NewsCandidate, VerificationResult

THAI_WEEKDAYS = {
    "Monday": "วันจันทร์",
    "Tuesday": "วันอังคาร",
    "Wednesday": "วันพุธ",
    "Thursday": "วันพฤหัสบดี",
    "Friday": "วันศุกร์",
    "Saturday": "วันเสาร์",
    "Sunday": "วันอาทิตย์",
}


def _first_fact_lines(bundle: EvidenceBundle, limit: int = 2) -> list[str]:
    """Build short fact bullets from approved evidence only."""

    facts: list[str] = []
    for item in bundle.allowed_items[:limit]:
        excerpt = item.excerpt.strip().replace("\n", " ")
        facts.append(f"{item.source}: {excerpt}")
    return facts


def write_standard_topic_post(
    candidate: CandidateTopic,
    verification: VerificationResult,
    bundle: EvidenceBundle,
    run_date: date,
    weekday_name: str,
) -> DraftPost:
    """Generate a concise Thai Facebook draft for standard math mode."""

    thai_weekday = THAI_WEEKDAYS.get(weekday_name, weekday_name)
    why_relevant = (
        f"วันที่ {run_date.isoformat()} ตรงกับธีม {thai_weekday} ของเพจ และหัวข้อนี้อยู่ในกรอบคณิตศาสตร์ที่สอดคล้องกับวันดังกล่าว"
    )
    body_lines = [
        f"วันนี้ภาควิชาคณิตศาสตร์ชวนมองเรื่อง {candidate.title}",
        "จากแหล่งอ้างอิงที่ตรวจสอบแล้ว หัวข้อนี้ช่วยให้เห็นว่าคณิตศาสตร์ไม่ได้มีแค่สูตร แต่มีบริบททางความคิดและพัฒนาการที่น่าสนใจ",
        f"สำหรับวันที่ {run_date.isoformat()} เราเลือกประเด็นนี้เพราะสอดคล้องกับธีมประจำ{thai_weekday} และเหมาะกับการชวนคิดต่อในมุมคณิตศาสตร์",
        "ถ้ามีหัวข้อหรือมุมมองที่อยากให้เพจชวนคุยเพิ่มเติม สามารถฝากไว้ได้ในคอมเมนต์",
    ]
    return DraftPost(
        content_mode="STANDARD_MATH_MODE",
        topic_title=candidate.title,
        why_relevant=why_relevant,
        body="\n\n".join(body_lines),
        fact_summary=_first_fact_lines(bundle),
        hashtags=["#คณิตศาสตร์", "#Mathematics", "#ภาควิชาคณิตศาสตร์"],
    )


def write_news_post(
    candidate: NewsCandidate,
    verification: VerificationResult,
    bundle: EvidenceBundle,
    run_date: date,
) -> DraftPost:
    """Generate a concise Thai Facebook draft for news mode."""

    why_relevant = (
        f"ข่าวนี้เผยแพร่เมื่อ {candidate.published_at[:10]} และยังอยู่ในช่วงเวลาข่าวที่กำหนด โดยเชื่อมโยงกับการให้เหตุผลเชิงคณิตศาสตร์และวิทยาศาสตร์อย่างชัดเจน"
    )
    body_lines = [
        "ข่าววิทยาศาสตร์วันนี้",
        candidate.summary,
        f"ประเด็นที่เชื่อมกับคณิตศาสตร์คือ {candidate.math_relevance}",
        "เราคัดข่าวนี้มาเพื่อชวนมองว่าการคิดเชิงปริมาณและการใช้แบบจำลองยังเป็นหัวใจสำคัญของการทำความเข้าใจโลก",
        "โพสต์นี้ยังรอการตรวจทานจากผู้ดูแลก่อนเผยแพร่เสมอ",
    ]
    return DraftPost(
        content_mode="NEWS_MODE",
        topic_title=candidate.title,
        why_relevant=why_relevant,
        body="\n\n".join(body_lines),
        fact_summary=_first_fact_lines(bundle),
        hashtags=["#ข่าววิทยาศาสตร์", "#คณิตศาสตร์", "#ScientificReasoning"],
    )
