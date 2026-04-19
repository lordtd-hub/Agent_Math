"""Topic planner for the Phase 3 MVP."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path

from .dedupe import calculate_duplicate_penalty, load_post_history
from .models import AppSettings, CandidateTopic, PlannerRun

THEME_CANDIDATE_LIBRARY: dict[str, list[dict[str, str | None]]] = {
    "history": [
        {
            "title": "Euler กับภาษาสัญลักษณ์ของคณิตศาสตร์สมัยใหม่",
            "slug": "euler-modern-notation",
            "angle": "historical_profile",
            "entity": "Leonhard Euler",
        },
        {
            "title": "Gauss กับจุดเปลี่ยนของทฤษฎีจำนวน",
            "slug": "gauss-number-theory-turning-point",
            "angle": "historical_profile",
            "entity": "Carl Friedrich Gauss",
        },
        {
            "title": "Ramanujan และพลังของการมองเห็นรูปแบบ",
            "slug": "ramanujan-pattern-insight",
            "angle": "historical_profile",
            "entity": "Srinivasa Ramanujan",
        },
        {
            "title": "Emmy Noether กับแนวคิดสมมาตรที่เปลี่ยนวิทยาศาสตร์",
            "slug": "noether-symmetry-impact",
            "angle": "historical_profile",
            "entity": "Emmy Noether",
        },
        {
            "title": "Euclid กับรากฐานของการพิสูจน์อย่างเป็นระบบ",
            "slug": "euclid-axiomatic-proof",
            "angle": "historical_profile",
            "entity": "Euclid",
        },
    ],
    "theorem": [
        {
            "title": "ทฤษฎีบทพีทาโกรัสในมุมที่มากกว่าสูตรสามเหลี่ยม",
            "slug": "pythagorean-theorem-beyond-formula",
            "angle": "theorem_spotlight",
            "entity": "Pythagorean theorem",
        },
        {
            "title": "ทฤษฎีบทมูลฐานของเลขคณิตและความพิเศษของจำนวนเฉพาะ",
            "slug": "fundamental-theorem-arithmetic-primes",
            "angle": "theorem_spotlight",
            "entity": "Fundamental theorem of arithmetic",
        },
        {
            "title": "ทฤษฎีบทของเบย์สกับการอัปเดตความเชื่อจากข้อมูลใหม่",
            "slug": "bayes-theorem-updating-belief",
            "angle": "theorem_spotlight",
            "entity": "Bayes' theorem",
        },
        {
            "title": "สูตรของออยเลอร์ที่เชื่อมจำนวนเชิงซ้อนกับตรีโกณมิติ",
            "slug": "euler-formula-complex-trig",
            "angle": "theorem_spotlight",
            "entity": "Euler's formula",
        },
        {
            "title": "ทฤษฎีเศษเหลือของจีนกับการแยกปัญหาใหญ่เป็นปัญหาเล็ก",
            "slug": "chinese-remainder-theorem-modular-thinking",
            "angle": "theorem_spotlight",
            "entity": "Chinese remainder theorem",
        },
    ],
    "puzzle": [
        {
            "title": "ปัญหาสะพานเคอนิกส์แบร์กกับจุดกำเนิดของกราฟ",
            "slug": "konigsberg-bridges-graph-origin",
            "angle": "puzzle_story",
            "entity": "Seven Bridges of Konigsberg",
        },
        {
            "title": "Birthday paradox ทำไมคนไม่มากก็ชนวันเกิดกันได้",
            "slug": "birthday-paradox-shared-birthday",
            "angle": "puzzle_story",
            "entity": "Birthday paradox",
        },
        {
            "title": "Magic square กับเสน่ห์ของการจัดตัวเลขให้สมดุล",
            "slug": "magic-square-balance-patterns",
            "angle": "puzzle_story",
            "entity": "Magic square",
        },
        {
            "title": "ปัญหาจับมือกันทั้งหมดกี่ครั้งและการคิดแบบนับคู่",
            "slug": "handshake-problem-counting-pairs",
            "angle": "puzzle_story",
            "entity": "Handshake problem",
        },
        {
            "title": "Monty Hall problem กับสัญชาตญาณที่มักพาเราพลาด",
            "slug": "monty-hall-intuition-trap",
            "angle": "puzzle_story",
            "entity": "Monty Hall problem",
        },
    ],
    "notation": [
        {
            "title": "สัญลักษณ์ = ทำไมคณิตศาสตร์ต้องการภาษาที่กระชับ",
            "slug": "equal-sign-compact-language",
            "angle": "notation_story",
            "entity": "Equal sign",
        },
        {
            "title": "เครื่องหมาย pi จากวงกลมสู่ภาษาสากลของคณิตศาสตร์",
            "slug": "pi-symbol-shared-language",
            "angle": "notation_story",
            "entity": "Pi",
        },
        {
            "title": "Sigma notation ช่วยให้รูปแบบยาว ๆ อ่านง่ายขึ้นอย่างไร",
            "slug": "sigma-notation-readable-patterns",
            "angle": "notation_story",
            "entity": "Sigma notation",
        },
        {
            "title": "f(x) เปลี่ยนวิธีที่เราเล่าความสัมพันธ์ของตัวแปรอย่างไร",
            "slug": "function-notation-variable-relationships",
            "angle": "notation_story",
            "entity": "Function notation",
        },
        {
            "title": "สัญลักษณ์เซตกับการจัดระเบียบความคิดทางคณิตศาสตร์",
            "slug": "set-notation-organizing-math-thought",
            "angle": "notation_story",
            "entity": "Set notation",
        },
    ],
    "applications": [
        {
            "title": "จำนวนเฉพาะกับเบื้องหลังการเข้ารหัสข้อมูล",
            "slug": "primes-and-cryptography",
            "angle": "real_life_application",
            "entity": "Prime numbers",
        },
        {
            "title": "GPS ใช้แนวคิดระยะทางสั้นที่สุดอย่างไร",
            "slug": "gps-shortest-path",
            "angle": "real_life_application",
            "entity": "Shortest path",
        },
        {
            "title": "ความน่าจะเป็นช่วยอ่านผลตรวจทางการแพทย์อย่างรอบคอบได้อย่างไร",
            "slug": "probability-medical-testing",
            "angle": "real_life_application",
            "entity": "Conditional probability",
        },
        {
            "title": "เมทริกซ์และพีชคณิตเชิงเส้นในงานบีบอัดภาพ",
            "slug": "linear-algebra-image-compression",
            "angle": "real_life_application",
            "entity": "Linear algebra",
        },
        {
            "title": "สมการเชิงอนุพันธ์กับการพยากรณ์อากาศ",
            "slug": "differential-equations-weather",
            "angle": "real_life_application",
            "entity": "Differential equations",
        },
    ],
}


def _base_score(theme_slug: str, position: int) -> float:
    """Return a deterministic base score before history penalties."""

    theme_bonus = {
        "history": 0.74,
        "theorem": 0.75,
        "puzzle": 0.73,
        "notation": 0.72,
        "applications": 0.76,
    }.get(theme_slug, 0.70)
    return max(0.5, theme_bonus - (position * 0.02))


def _build_candidate(
    template: dict[str, str | None],
    theme_slug: str,
    theme_label: str,
    run_date: date,
    position: int,
) -> CandidateTopic:
    """Build a candidate topic from the theme library."""

    reasons = [
        f"Matches the {run_date.strftime('%A')} theme: {theme_label}.",
        f"Suitable for Thai-language drafting after verification on {run_date.isoformat()}.",
        "Any factual claims still require trusted-source retrieval and explicit date-link verification before posting.",
    ]
    return CandidateTopic(
        title=str(template["title"]),
        slug=str(template["slug"]),
        theme_slug=theme_slug,
        theme_label=theme_label,
        angle=str(template["angle"]),
        entity=str(template["entity"]) if template["entity"] else None,
        date_link_type="weekday_theme",
        date_link_explanation=(
            f"This candidate fits the scheduled weekday theme for {run_date.isoformat()}, "
            f"which is {theme_label.lower()}."
        ),
        reasons=reasons,
        base_score=_base_score(theme_slug, position),
    )


def plan_topics(
    run_date: date,
    weekday_name: str,
    theme_slug: str,
    theme_label: str,
    settings: AppSettings,
) -> PlannerRun:
    """Generate and score multiple candidates for the current weekday."""

    templates = THEME_CANDIDATE_LIBRARY.get(theme_slug, [])
    history = load_post_history(settings.post_history_path)
    candidates: list[CandidateTopic] = []

    for index, template in enumerate(templates):
        candidate = _build_candidate(template, theme_slug, theme_label, run_date, index)
        duplicate_penalty, dedupe_notes = calculate_duplicate_penalty(candidate, history, run_date, settings)
        candidates.append(
            CandidateTopic(
                title=candidate.title,
                slug=candidate.slug,
                theme_slug=candidate.theme_slug,
                theme_label=candidate.theme_label,
                angle=candidate.angle,
                entity=candidate.entity,
                date_link_type=candidate.date_link_type,
                date_link_explanation=candidate.date_link_explanation,
                reasons=[*candidate.reasons, *dedupe_notes],
                base_score=candidate.base_score,
                duplicate_penalty=duplicate_penalty,
                final_score=max(0.0, candidate.base_score - duplicate_penalty),
                requires_retrieval=True,
            )
        )

    ranked = sorted(candidates, key=lambda item: item.final_score, reverse=True)
    selected = ranked[0] if ranked else None
    return PlannerRun(
        run_date=run_date,
        weekday_name=weekday_name,
        theme_slug=theme_slug,
        theme_label=theme_label,
        output_language=settings.output_language,
        candidates=ranked[: settings.planner_candidate_target],
        selected_candidate=selected,
    )


def write_planner_debug(run: PlannerRun, cache_dir: Path, generated_at: datetime | None = None) -> Path:
    """Store planner output for audit and debugging."""

    timestamp = (generated_at or datetime.now(UTC)).replace(microsecond=0).isoformat()
    payload = {
        "run_date": run.run_date.isoformat(),
        "weekday_name": run.weekday_name,
        "theme_slug": run.theme_slug,
        "theme_label": run.theme_label,
        "output_language": run.output_language,
        "selected_candidate": asdict(run.selected_candidate) if run.selected_candidate else None,
        "candidates": [asdict(candidate) for candidate in run.candidates],
        "generated_at": timestamp,
    }
    path = cache_dir / f"{run.run_date.isoformat()}_planner_candidates.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
