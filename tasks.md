# tasks.md

## Development Strategy
Build the system in phases. Complete and test each phase before moving on.

This task plan reflects the updated workflow:

1. Try verified recent news first.
2. If no valid news passes verification, fall back to standard math topic mode.
3. Always require human approval before any posting action.

---

## Phase 1: Repository scaffolding
### Task 1.1
Create the repository structure.

### Task 1.2
Add base documentation files:
- README.md
- specs/requirements.md
- specs/design.md
- specs/tasks.md
- specs/source_policy.md
- specs/editorial_policy.md

### Task 1.3
Add `.env.example` with placeholders for:
- FACEBOOK_PAGE_ACCESS_TOKEN
- FACEBOOK_PAGE_ID
- POST_MODE
- TIMEZONE
- CONFIDENCE_THRESHOLD

### Task 1.4
Set up Python project dependencies and base package structure.

**Definition of done**
- repo structure exists
- app starts without crashing
- configuration loading works

---

## Phase 2: Weekday scheduling and base config
### Task 2.1
Implement weekday detection utility.

### Task 2.2
Implement scheduler entrypoint that exits cleanly on weekends.

### Task 2.3
Create config files:
- `weekday_themes.yaml`
- `trusted_sources.yaml`
- `settings.yaml`

### Task 2.4
Add tests for weekend skipping behavior.

**Definition of done**
- weekday runs continue
- weekend runs exit without generating draft
- tests pass

---

## Phase 3: Topic planner
### Task 3.1
Implement candidate topic model.

### Task 3.2
Implement planner that generates 3-5 candidates based on:
- date relevance
- weekday theme
- post history

### Task 3.3
Add candidate scoring logic.

### Task 3.4
Add de-duplication penalties using post history.

### Task 3.5
Store planner output for debugging.

**Definition of done**
- planner produces multiple candidates
- candidates contain reasons
- repeated recent topics are penalized

---

## Phase 4: News detector and selection
### Task 4.1
Add `news` configuration to control:
- enable/disable news mode
- recency window
- minimum source count
- multi-source requirement for major claims

### Task 4.2
Implement a news candidate model.

### Task 4.3
Implement a news detector that searches for recent items related to:
- mathematics
- science
- astronomy

### Task 4.4
Filter news candidates by:
- trusted source allowlist
- recency window
- clear non-speculative factual content
- explainable math/science relevance

### Task 4.5
Implement decision logic:
- if valid verified news exists -> use `NEWS_MODE`
- else -> use standard math topic mode

### Task 4.6
Store news candidate/debug output for audit purposes.

**Definition of done**
- system can evaluate recent trusted news
- invalid or weak news is rejected
- system falls back safely to topic mode when needed

---

## Phase 5: Retrieval layer
### Task 5.1
Implement source allowlist loading from `trusted_sources.yaml`.

### Task 5.2
Implement retrieval interface that can query approved sources.

### Task 5.3
Implement retrieval for both:
- news candidates
- standard math topic candidates

### Task 5.4
Normalize evidence into a consistent internal format.

### Task 5.5
Capture source metadata:
- title
- source
- url
- excerpt/summary
- date metadata if available
- source tier

### Task 5.6
Store raw evidence bundles for audit purposes.

**Definition of done**
- each candidate can produce an evidence bundle
- evidence is normalized
- non-approved sources are rejected or ignored

---

## Phase 6: Verification engine
### Task 6.1
Define verification result schema.

### Task 6.2
Implement fact check rules for key claims.

### Task 6.3
Implement date linkage verification.

### Task 6.4
Implement news recency verification.

### Task 6.5
Implement news relevance verification:
- explain why the news fits a mathematics/scientific reasoning page
- reject weak or forced relevance

### Task 6.6
Implement conflict detection logic.

### Task 6.7
Implement quote verification rule.

### Task 6.8
Reject speculative or weakly sourced research/news items.

### Task 6.9
Implement confidence scoring.

### Task 6.10
Create tests for:
- conflicting sources
- weak date linkage
- weak news recency
- speculative news
- unverifiable quote
- high-confidence valid case
- valid news case

**Definition of done**
- verifier returns structured result
- conflict cases are blocked
- confidence scoring works
- tests pass

---

## Phase 7: Thai post writer
### Task 7.1
Define Thai editorial template.

### Task 7.2
Implement writer that turns verified topic into:
- headline/hook
- body
- short close
- optional hashtags

### Task 7.3
Support two writing modes:
- `NEWS_MODE`
- `STANDARD_MATH_MODE`

### Task 7.4
Ensure writer references only verified claims.

### Task 7.5
Add style constraints:
- concise
- readable
- academically safe
- not overly technical

**Definition of done**
- writer produces clean Thai post drafts
- no unsupported claims leak into final post

---

## Phase 8: Review package generation
### Task 8.1
Generate markdown review package.

### Task 8.2
Generate JSON review package.

### Task 8.3
Store outputs by date in:
- `outputs/daily_reviews/`
- `outputs/verification_json/`

### Task 8.4
Add status field:
- PENDING_REVIEW
- NEEDS_REVISION
- BLOCKED_LOW_CONFIDENCE

### Task 8.5
Ensure every package includes:
- topic
- why it matches today or why the news is relevant
- Thai draft
- fact summary
- short references
- full references
- verification notes
- confidence score
- status

**Definition of done**
- each run creates review artifacts
- reviewer can read the markdown package directly

---

## Phase 9: Manual approval workflow
### Task 9.1
Design approval file format.

### Task 9.2
Implement approval reader/validator.

### Task 9.3
Block publish attempts unless approval status is `APPROVED`.

### Task 9.4
Support reviewer notes and revision requests.

### Task 9.5
Add tests for approval gate logic.

**Definition of done**
- no publish call can occur without explicit approval
- invalid approval files fail safely

---

## Phase 10: Facebook publishing
### Task 10.1
Implement Facebook publisher module.

### Task 10.2
Support `approve_then_post`.

### Task 10.3
Support `approve_then_schedule`.

### Task 10.4
Log Facebook responses and errors.

### Task 10.5
Add dry-run mode for safe testing.

**Definition of done**
- approved content can be published or scheduled
- dry-run testing works
- failures are logged clearly

---

## Phase 11: History and de-duplication improvements
### Task 11.1
Store post history after approval/publication.

### Task 11.2
Track:
- mathematician name
- theorem/event tag
- theme category
- mode used (`NEWS_MODE` or `STANDARD_MATH_MODE`)
- date used
- publish result

### Task 11.3
Improve repeat-avoidance scoring.

### Task 11.4
Add tests for duplicate suppression.

**Definition of done**
- repeated content is reduced
- history updates reliably after each run

---

## Phase 12: GitHub Actions automation
### Task 12.1
Create `weekday_draft.yml` to generate weekday drafts automatically.

### Task 12.2
Create `publish_after_approval.yml` to publish after an approval artifact is present.

### Task 12.3
Ensure timezone and cron settings align with Asia/Bangkok.

### Task 12.4
Document required secrets setup.

**Definition of done**
- weekday drafts run automatically
- publishing workflow is separate and approval-gated

---

## Phase 13: Operational hardening
### Task 13.1
Add structured logging.

### Task 13.2
Add retry policy for transient failures.

### Task 13.3
Add fallback behavior when no strong topic exists.

### Task 13.4
Improve audit trail and output naming consistency.

### Task 13.5
Document troubleshooting steps.

**Definition of done**
- logs are useful
- failure modes are safe
- operations are understandable

---

## Suggested MVP order
Implement in this order:
1. repo scaffold
2. weekday scheduler
3. planner
4. news detector
5. retriever
6. verifier
7. writer
8. review package
9. approval gate
10. Facebook publishing
11. automation polish

## Strict guardrails
These rules must remain true throughout development:
- never publish without approval
- never auto-post news without approval
- never invent references
- never claim date relevance without evidence
- never claim news relevance without evidence
- never use unverifiable quotes
- never ignore conflicting sources
- never post speculative research
- always fall back if news is weak
- prefer no post over a weak post

## Suggested first commit sequence
1. `init repo and config`
2. `add weekday scheduler`
3. `add planner and candidate model`
4. `add news detection and selection`
5. `add retrieval normalization`
6. `add verifier and tests`
7. `add Thai writer`
8. `add review package builder`
9. `add approval gate`
10. `add Facebook publisher`
11. `add GitHub Actions workflows`
