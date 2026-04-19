# design.md

## System Overview
This project is a **human-in-the-loop AI content agent** for a Mathematics Department Facebook page.

The system generates one weekday draft about a mathematics-related topic tied to the current date or weekday theme, verifies the content carefully, and presents it for human approval before any publishing step.

## Design Goals
- Strong factual reliability
- Clear date-based relevance
- Mandatory human review
- Easy maintenance
- Good audit trail
- Safe failure behavior

## Architecture

```text
Scheduler
  -> Topic Planner
  -> Retriever
  -> Verifier
  -> Writer
  -> Review Package Builder
  -> Approval Gate
  -> Publisher
  -> History/Logging
```

## Main Components

### 1. Scheduler
Responsible for triggering the workflow on weekdays only.

**Responsibilities**
- Run every Monday–Friday
- Skip weekends
- Pass current date and weekday into pipeline

**Recommended implementation**
- GitHub Actions cron schedule
- Timezone: Asia/Bangkok

---

### 2. Topic Planner
Generates candidate topics for the day.

**Input**
- current date
- weekday
- topic history
- optional weekday theme map

**Output**
- list of candidate topics with reasons and preliminary scores

**Example weekday themes**
- Monday: mathematician birthdays / history
- Tuesday: theorem spotlight
- Wednesday: puzzle or paradox
- Thursday: notation, symbols, language of mathematics
- Friday: mathematics in real life / applications

**Planner rules**
- Generate 3–5 candidates
- Prefer strong date relevance
- Penalize recent duplicates
- Avoid niche claims with weak source coverage

---

### 3. Retriever
Collects evidence from trusted sources only.

**Input**
- candidate topic
- source allowlist

**Output**
- evidence bundle per candidate

**Evidence should include**
- title
- source URL
- publication or page metadata if available
- relevant excerpt or summary
- source type
- confidence notes

**Trusted sources**
Should be defined in `source_policy.md` and optionally `trusted_sources.yaml`.

Examples of source tiers:
- Tier 1: primary or authoritative institutional sources
- Tier 2: high-quality mathematical reference sources
- Tier 3: general background sources, not sufficient alone for critical claims

---

### 4. Verifier
This is the most important module.

**Input**
- candidate topic
- evidence bundle
- current date

**Output**
- verification result object

**Checks**
1. Are the core facts supported?
2. Are at least two reliable sources available for important claims?
3. Is the date linkage true and explicit?
4. Are there conflicts between sources?
5. Is any quote unverifiable?
6. Is the explanation accurate but still accessible?

**Hard rules**
- If key sources conflict -> require human review
- If date linkage is weak -> do not publish
- If quote cannot be verified -> remove quote
- If confidence below threshold -> mark blocked or revision-needed

**Suggested result schema**
```json
{
  "publishable": false,
  "confidence": 0.82,
  "topic_title": "",
  "date_link_type": "",
  "fact_checks": [],
  "conflicts": [],
  "required_human_review": true,
  "reason": ""
}
```

---

### 5. Writer
Transforms the verified topic into a Thai Facebook post draft.

**Style goals**
- concise
- readable
- academically safe
- interesting for a broad university audience
- not overly casual
- not too technical unless clearly explained

**Suggested post structure**
1. Hook
2. Main math fact
3. Why today is relevant
4. Short closing line
5. Optional hashtags

**Do not**
- invent quotes
- overstate uncertain historical claims
- use unexplained jargon heavily
- produce long walls of text

---

### 6. Review Package Builder
Creates outputs for the human reviewer.

**Outputs**
- human-readable markdown file
- machine-readable JSON file

**Markdown includes**
- proposed topic
- why it matches today
- post draft
- fact summary
- short references
- full references
- verification notes
- confidence
- status

**JSON includes**
- candidate list
- selected topic
- evidence metadata
- verification result
- timestamps
- status

---

### 7. Approval Gate
Blocks any publishing until human approval exists.

**Allowed actions**
- approve
- reject
- request revision
- schedule later

**Possible implementations**
- local CLI approval file
- GitHub issue/comment workflow
- simple web panel
- manual edit of approval JSON

**MVP recommendation**
Use a simple approval artifact such as:
```json
{
  "date": "2026-04-20",
  "status": "APPROVED",
  "reviewer": "admin",
  "notes": "OK to publish"
}
```

---

### 8. Publisher
Posts to Facebook only after approval.

**Input**
- approved draft
- publishing mode
- Facebook page token/settings

**Modes**
- `draft_only`: never call Facebook
- `approve_then_post`: publish immediately after approval
- `approve_then_schedule`: create scheduled post after approval

**Responsibilities**
- validate approved state
- send post payload
- capture response
- log outcome
- handle token/auth failure cleanly

---

### 9. History and De-duplication
Avoids repetitive topics.

**Store**
- date
- topic
- subcategory
- key mathematician/theorem/event
- posting outcome

**Rules**
- avoid repeating same exact topic within recent window
- penalize same mathematician too frequently
- allow reuse only if angle is substantially different

---

## Proposed Folder Structure

```text
math-content-agent/
  specs/
    requirements.md
    design.md
    tasks.md
    source_policy.md
    editorial_policy.md
  config/
    trusted_sources.yaml
    weekday_themes.yaml
    settings.yaml
  data/
    post_history.csv
    candidate_cache/
  prompts/
    planner.md
    verifier.md
    writer.md
  src/
    scheduler.py
    planner.py
    retriever.py
    verifier.py
    writer.py
    package_builder.py
    approval.py
    publisher_facebook.py
    dedupe.py
    models.py
    utils.py
  outputs/
    daily_reviews/
    verification_json/
    logs/
  tests/
    test_verifier.py
    test_dedupe.py
    test_weekday_logic.py
  .github/workflows/
    weekday_draft.yml
    publish_after_approval.yml
  README.md
  .env.example
```

## Runtime Flow

```text
1. Scheduler starts weekday run
2. Planner generates candidate topics
3. Retriever gathers evidence
4. Verifier scores evidence and date relevance
5. Best valid topic is selected
6. Writer drafts Thai Facebook post
7. Review package is created
8. System waits for human approval
9. If approved:
      - post now OR schedule
   Else:
      - stop safely
10. Record logs and history
```

## Confidence Policy
Suggested thresholds:
- `>= 0.90` : high confidence, still requires approval
- `0.75 - 0.89` : acceptable draft, highlight notes for reviewer
- `< 0.75` : block publishing and mark for revision/review

## Error Handling
### Retrieval failure
- log error
- do not publish
- optionally create a fallback review note

### Weak references
- mark low confidence
- do not publish

### Conflicting dates
- flag conflict clearly
- require reviewer attention

### Facebook API failure
- preserve approved draft
- log publish error
- allow retry

## Security Considerations
- Keep Facebook tokens in secrets or environment variables
- Never commit secrets to repository
- Log minimal credential information
- Validate approval input before publishing

## Recommended MVP
For MVP, prioritize:
1. weekday draft generation
2. strong verification
3. markdown review package
4. manual approval
5. Facebook posting after approval

Do not start with a full dashboard unless necessary.
