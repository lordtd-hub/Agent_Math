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

BRANDED_HASHTAGS = ["#คณิต(วิทย์)มรส.", "#MathSCISRU"]

STANDARD_THEME_EXPLANATIONS = {
    "history": "ธีมของวันจันทร์เน้นประวัติศาสตร์คณิตศาสตร์และนักคณิตศาสตร์สำคัญ",
    "theorem": "ธีมของวันอังคารเน้นการหยิบทฤษฎีบทสำคัญมาอธิบายอย่างเข้าถึงได้",
    "puzzle": "ธีมของวันพุธเน้นโจทย์ชวนคิดและปริศนาที่เปิดมุมมองทางคณิตศาสตร์",
    "notation": "ธีมของวันพฤหัสบดีเน้นสัญลักษณ์ ภาษา และวิธีสื่อความคิดทางคณิตศาสตร์",
    "applications": "ธีมของวันศุกร์เน้นการประยุกต์ใช้คณิตศาสตร์ในชีวิตจริง",
}


def _first_fact_lines(bundle: EvidenceBundle, limit: int = 2) -> list[str]:
    """Build short fact bullets from approved evidence only."""

    facts: list[str] = []
    for item in bundle.allowed_items[:limit]:
        excerpt = item.excerpt.strip().replace("\n", " ")
        facts.append(f"{item.source}: {excerpt}")
    return facts


def _standard_why_relevant(candidate: CandidateTopic, run_date: date, weekday_name: str) -> str:
    """Explain the weekday linkage in Thai using the configured theme logic."""

    thai_weekday = THAI_WEEKDAYS.get(weekday_name, weekday_name)
    theme_explanation = STANDARD_THEME_EXPLANATIONS.get(
        candidate.theme_slug,
        f"ธีมของ{thai_weekday}ใช้คัดเลือกประเด็นคณิตศาสตร์ที่เหมาะกับการสื่อสารในวันนั้น",
    )
    return (
        f"วันที่ {run_date.isoformat()} ตรงกับ{thai_weekday} และ {theme_explanation} "
        f"หัวข้อ \"{candidate.title}\" จึงเชื่อมกับวันผ่านกรอบธีมนี้อย่างชัดเจน "
        f"ไม่ใช่เพียงเพราะเป็นเรื่องคณิตศาสตร์ทั่วไป"
    )


def write_standard_topic_post(
    candidate: CandidateTopic,
    verification: VerificationResult,
    bundle: EvidenceBundle,
    run_date: date,
    weekday_name: str,
) -> DraftPost:
    """Generate a concise Thai Facebook draft for standard math mode."""

    del verification
    thai_weekday = THAI_WEEKDAYS.get(weekday_name, weekday_name)
    why_relevant = _standard_why_relevant(candidate, run_date, weekday_name)
    body_lines = [
        f"วันนี้ภาควิชาคณิตศาสตร์ชวนมองเรื่อง {candidate.title}",
        "จากแหล่งอ้างอิงที่ตรวจสอบแล้ว หัวข้อนี้ช่วยให้เห็นว่าคณิตศาสตร์ไม่ได้มีแค่สูตร แต่มีบริบททางความคิดและพัฒนาการที่น่าสนใจ",
        f"สำหรับวันที่ {run_date.isoformat()} เราเลือกประเด็นนี้เพราะตรงกับธีมประจำ{thai_weekday}ของเพจ ซึ่งเน้นการเล่าเรื่องคณิตศาสตร์ให้เห็นความหมายและที่มาอย่างชัดเจน",
        "ถ้ามีหัวข้อหรือมุมมองที่อยากให้เพจชวนคุยเพิ่มเติม สามารถฝากไว้ได้ในคอมเมนต์",
    ]
    return DraftPost(
        content_mode="STANDARD_MATH_MODE",
        topic_title=candidate.title,
        why_relevant=why_relevant,
        body="\n\n".join(body_lines),
        fact_summary=_first_fact_lines(bundle),
        hashtags=list(BRANDED_HASHTAGS),
    )


def write_news_post(
    candidate: NewsCandidate,
    verification: VerificationResult,
    bundle: EvidenceBundle,
    run_date: date,
) -> DraftPost:
    """Generate a concise Thai Facebook draft for news mode."""

    del verification
    del run_date
    why_relevant = (
        f"ข่าวนี้เผยแพร่เมื่อ {candidate.published_at[:10]} และยังอยู่ในช่วงข่าวล่าสุดที่ระบบอนุญาต "
        f"โดยเชื่อมกับคณิตศาสตร์ผ่านประเด็น {candidate.math_relevance}"
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
        hashtags=list(BRANDED_HASHTAGS),
    )
