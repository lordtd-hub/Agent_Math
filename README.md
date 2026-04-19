# Math Content Agent

Human-in-the-loop weekday content pipeline for a university Mathematics Department Facebook page.

The MVP is being built phase by phase from the specs in `specs/requirements.md`, `specs/design.md`, `specs/tasks.md`, `specs/source_policy.md`, and `specs/editorial_policy.md`.

## Guardrails

- Never publish automatically without explicit human approval.
- Generate one weekday Thai Facebook draft only on Monday-Friday.
- Verify references carefully and verify date relevance explicitly.
- Produce a daily review package for the admin before any posting step.

## Current Status

Core MVP foundations are in place:

- repository scaffold
- config files
- Python package structure
- weekday scheduler entrypoint
- Thai output language default
- topic planner with candidate caching
- news-first detection with safe fallback to topic mode
- retrieval normalization with trusted-source filtering
- verification engine for topic mode and news mode
- Thai draft writer for both modes
- markdown and JSON review package generation
- strict manual approval gate before publishing
- Facebook publisher with draft-only, post, schedule, and dry-run modes
- end-to-end generate and publish CLI orchestration
- GitHub Actions weekday email workflow for morning review delivery
- weekend skip tests

Operational hardening can continue from this baseline, but the daily email automation path is now wired for GitHub Actions.

## Quick Start

1. Copy `.env.example` to `.env` if you want environment overrides.
2. Generate the daily review package:

```powershell
$env:PYTHONPATH='src'
& 'C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe' -m math_content_agent.scheduler generate-review
```

3. After a human marks the approval artifact as `APPROVED`, run the publish step:

```powershell
$env:PYTHONPATH='src'
& 'C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe' -m math_content_agent.scheduler publish-approved --review-date 2026-04-20
```

4. Run the tests:

```powershell
$env:PYTHONPATH='src'
& 'C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe' -m unittest discover -s tests -v
```

## GitHub Weekday Email

The repository includes [weekday_email.yml](/C:/Users/User/Documents/Agent_math/.github/workflows/weekday_email.yml), which runs every Monday-Friday at 06:00 Asia/Bangkok and emails the review package to the address configured in `REVIEW_EMAIL_TO`.

Behavior:

- runs `generate-review`
- keeps `POST_MODE=draft_only`
- keeps `FACEBOOK_DRY_RUN=true`
- sends the review email after generation
- uploads review artifacts to the workflow run

Required GitHub Actions secrets:

- `REVIEW_EMAIL_TO`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`
- `EMAIL_FROM`

Recommended setup notes:

- Use an SMTP account or app password dedicated to automation.
- The workflow schedule uses UTC under the hood, but it is already mapped to 06:00 Bangkok time.
- If you want to test it immediately from the Actions tab on a weekend, run `workflow_dispatch` and set `review_now` to a weekday timestamp such as `2026-04-20T06:00:00+07:00`.

## GitHub eDocument Digest

The repository also includes [edocument_digest.yml](/C:/Users/User/Documents/Agent_math/.github/workflows/edocument_digest.yml), which runs a read-only SRU eDocument digest every Monday-Friday at 11:30 and 15:30 Asia/Bangkok.

Behavior:

- logs into the SRU eDocument portal
- opens Saraban pending receive documents
- filters to items sent today or yesterday that are still `รอรับ`
- opens each matching detail page and collects metadata plus attachment names when available
- sends one Thai summary email
- does not accept documents yet in this phase

Required GitHub Actions secrets:

- `EDOC_USERNAME`
- `EDOC_PASSWORD`
- `EDOC_EMAIL_TO`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`
- `EMAIL_FROM`

Recommended setup notes:

- Start with this workflow as read-only and confirm the summaries look correct before adding any accept action.
- Keep the eDocument account scope as narrow as possible.
- The workflow uploads only the JSON digest log, not the raw documents or downloaded attachments.
- For manual testing from the Actions tab, use `workflow_dispatch` with `run_now`, for example `2026-04-20T11:30:00+07:00`.

## Project Layout

```text
config/
data/
outputs/
prompts/
specs/
src/math_content_agent/
tests/
```
