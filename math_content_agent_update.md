# Mathematics Facebook Content Agent (Updated Specification)

## Overview
This system generates ONE high-quality Thai Facebook post per weekday (Monday–Friday) for a Mathematics Department page.

The system supports:
- Mathematical facts tied to date/weekday
- Verified science/mathematics/astronomy news
- Strong reference validation
- Mandatory human approval before posting

---

## CRITICAL RULE (MUST FOLLOW)
The system MUST NEVER publish automatically without explicit human approval.

---

## Daily Workflow

Each weekday:

1. Try to find relevant NEWS
2. If valid → use NEWS mode
3. If not → fallback to MATH TOPIC mode
4. Generate draft
5. Send to human reviewer
6. Wait for approval
7. Publish or schedule AFTER approval only

---

## NEW FEATURE: News Override Mode

### Goal
Prioritize recent high-quality news when available.

---

## News Selection Criteria (STRICT)

A news item is valid ONLY IF:

### 1. Domain
Must be related to:
- mathematics
- science
- astronomy

### 2. Recency
- within 3–7 days (configurable)

### 3. Source Quality
- from trusted sources only
- no blogs, clickbait, or unknown sites

### 4. Verification
- factually clear
- not speculative
- preferably supported by multiple sources

### 5. Relevance
- must be explainable
- MUST connect to mathematics or scientific reasoning

---

## Decision Logic

IF valid_news_found AND verification_passed:
    USE NEWS MODE
ELSE:
    USE STANDARD MATH TOPIC MODE

---

## System Pipeline

Scheduler (Mon–Fri only)
  -> News Detector
        -> if valid → Verifier → Writer → Review Package
        -> if not → Topic Planner → Retriever → Verifier → Writer → Review Package
  -> Approval Gate
  -> Publisher

---

## Output Requirements (EVERY POST)

Each draft MUST include:

- Topic
- Why it matches today OR why news is relevant
- Thai Facebook post draft
- Fact summary
- References (short + full)
- Verification notes
- Confidence score
- Status = PENDING_REVIEW

---

## NEWS POST FORMAT (Thai)

🔬 ข่าววิทยาศาสตร์วันนี้

[สรุปข่าว 2–4 บรรทัด]

📌 ประเด็นสำคัญ
- ...
- ...

📖 เกี่ยวข้องกับคณิตศาสตร์ยังไง
- ...

🔎 อ้างอิง
1. ...
2. ...

---

## STANDARD MATH POST FORMAT (Thai)

- Hook
- Math fact / theorem / person
- Why today is relevant
- Short explanation
- References

---

## Verification Rules

The system MUST:

- verify facts with reliable sources
- verify date linkage (for non-news)
- verify recency (for news)
- detect conflicting sources
- reject unverifiable quotes

---

## Hard Safety Rules

- NEVER publish without approval
- NEVER invent references
- NEVER use unverifiable quotes
- NEVER post speculative research
- NEVER rely on weak sources
- ALWAYS fallback if uncertain
- prefer NO POST over WRONG POST

---

## Configuration

news:
  enabled: true
  max_age_days: 7
  min_sources: 1
  require_multi_source_for_major_claims: true

posting:
  mode: approve_then_post  # or draft_only / approve_then_schedule

verification:
  confidence_threshold: 0.75

---

## Status Values

- PENDING_REVIEW
- APPROVED
- REJECTED
- NEEDS_REVISION
- BLOCKED_LOW_CONFIDENCE
- PUBLISHED
- SCHEDULED

---

## Approval Flow

The system MUST:

1. Generate draft
2. Wait for human action
3. Accept only:
   - approve
   - reject
   - revise

Only AFTER approval:
- post immediately OR
- schedule post

---

## Testing Requirements

System must include tests for:

- valid news → selected
- weak news → rejected
- no news → fallback works
- conflicting sources → blocked
- approval required → enforced

---

## Final Goal

Build a system that behaves like:

"AI-assisted academic content curator with strict verification and human control"

NOT a fully autonomous posting bot.

---

## IMPORTANT PRIORITY ORDER

1. Accuracy
2. Reference reliability
3. Correct reasoning
4. Human control
5. Automation

---

## Summary

This system is:

- Math content generator
- Science/news curator
- Reference-verified pipeline
- Human-in-the-loop publishing system

Designed for real academic usage.
