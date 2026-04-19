# requirements.md

## Project
Weekday Mathematics Content Agent for a university Mathematics Department Facebook page.

## Goal
Build an AI-assisted content pipeline that generates one mathematics-related Facebook post draft every weekday (Monday–Friday), with strong reference checking, explicit date relevance, and mandatory human review before publishing.

## Core Principle
The system must **never publish automatically without explicit human approval**.

## Primary Use Case
Each weekday, the system should:
1. Find candidate math topics connected to the current date or weekday theme.
2. Retrieve evidence from trusted sources.
3. Verify facts and date linkage carefully.
4. Generate one Thai Facebook draft.
5. Present a review package to the human admin.
6. Wait for approval.
7. Only after approval, publish or schedule the post.

## Users
- **Admin/Reviewer**: mathematics department staff member who reads and approves the draft.
- **System**: AI agent pipeline with retrieval, verification, writing, and publishing modules.

## Scope
### In scope
- Weekday scheduling (Mon–Fri only)
- Topic discovery
- Reference gathering
- Fact verification
- Date relevance verification
- Thai Facebook draft generation
- Human approval workflow
- Publishing to Facebook after approval
- Logging and evidence storage
- Duplicate avoidance

### Out of scope for MVP
- Instagram, X, Threads, LINE OA integration
- Full graphic/image generation pipeline
- Student-facing chatbot
- Full CMS or multi-admin dashboard
- Automatic weekend posting

## Functional Requirements

### FR-1 Weekday generation
The system must generate exactly one draft package per weekday and skip Saturday and Sunday.

### FR-2 Topic relevance
The system must select topics that are linked to at least one of the following:
- mathematician birth date
- mathematician death date
- theorem/publication milestone
- historical mathematical event
- weekday theme (e.g. theorem day, notation day, puzzle day)

### FR-3 Candidate topics
The system must initially generate multiple candidate topics and score them before selecting one final topic.

### FR-4 Trusted-source retrieval
The system must retrieve evidence only from trusted or pre-approved sources listed in a source policy file.

### FR-5 Reference quality
For each important factual claim, the system should verify against at least two reliable sources whenever possible.

### FR-6 Date linkage verification
The system must explicitly verify why the selected topic matches the current date or theme.

### FR-7 Conflict handling
If sources conflict on a key fact or on the date linkage, the system must mark the draft as requiring review and must not publish.

### FR-8 Quote verification
The system must not use a quote unless its wording and source are verified.

### FR-9 Thai post generation
The system must produce a concise Thai Facebook post suitable for a university mathematics page.

### FR-10 Review package
The daily review package must include:
- proposed topic
- why it matches today
- Thai Facebook draft
- fact summary
- short references
- full references
- verification notes
- confidence score
- final status

### FR-11 Approval requirement
Publishing must require an explicit human approval action.

### FR-12 Publish modes
The system must support:
- `draft_only`
- `approve_then_post`
- `approve_then_schedule`

### FR-13 Logging
The system must log:
- generated candidates
- selected topic
- source list
- verification result
- final draft
- approval action
- publishing result
- errors

### FR-14 History and de-duplication
The system must store past topics/posts and reduce repetition across recent posts.

### FR-15 Failure-safe behavior
If retrieval fails, references are weak, or confidence is too low, the system must produce a review-only draft or no draft, but must not publish.

## Non-Functional Requirements

### NFR-1 Accuracy first
Accuracy and reference integrity are more important than output speed.

### NFR-2 Auditability
Every published or proposed post must be traceable back to sources and verification notes.

### NFR-3 Maintainability
The codebase must be modular and easy to update with new source rules and editorial rules.

### NFR-4 Observability
Errors and decision outcomes must be visible via logs.

### NFR-5 Configurability
The system must allow:
- posting mode changes
- schedule changes
- confidence threshold changes
- source allowlist changes
- editorial tone adjustments

## Data Requirements

### Input data
- current date
- weekday name
- trusted source list
- editorial policy
- source policy
- recent post history
- runtime secrets (API keys/tokens)

### Output data
- daily review markdown
- machine-readable verification JSON
- approval state
- publish result log

## Daily Review Package Format
The system should create a markdown file like:

```md
# Daily Math Post Draft - YYYY-MM-DD

## Proposed Topic
...

## Why this matches today
...

## Draft Facebook Post
...

## Fact Summary
- ...
- ...

## Short References
1. ...
2. ...

## Full References
1. ...
2. ...

## Verification Notes
- ...
- ...

## Confidence
0.00-1.00

## Status
PENDING_REVIEW
```

## Status Values
- `PENDING_REVIEW`
- `APPROVED`
- `REJECTED`
- `NEEDS_REVISION`
- `PUBLISHED`
- `SCHEDULED`
- `BLOCKED_LOW_CONFIDENCE`

## Acceptance Criteria
A build is acceptable when:
1. It creates a weekday draft package automatically.
2. It skips weekends.
3. It includes references and verification notes.
4. It never publishes without approval.
5. It can publish to Facebook after approval.
6. It stores logs and avoids obvious duplicates.
