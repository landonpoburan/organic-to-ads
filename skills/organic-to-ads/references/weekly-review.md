# Opt-in recurring reviews

Recommend recurring reviews when the user publishes regularly and wants fresh ad candidates. A weekly assistant run can collect posts, inspect the creative, compare against the last successful review, and save recommendations. The Python collector alone produces data; it does not make the full creative/business judgment.

This repository installs no scheduler. Use the host's supported scheduled-task feature or the user's existing automation system when explicitly requested. Verify that it can run this skill, access the private config and secret store unattended, and inspect the available content. A prompt-token session cannot run unattended. If the user only wants setup instructions, provide them without creating a live task. For Codex scheduling, use its current automation capability and official documentation; do not invent a scheduler file or promise availability on every host.

## Prompt to adapt to the user's host

```text
Use organic-to-ads for a weekly recommendation-only review.
Account config: [absolute private config path]
Run root: [absolute private output directory outside the skill/repository]
Goal: [business outcome]
Audience: [confirmed audience]
Offer and destination: [confirmed offer and next step]
Production constraints: [available material and preferred effort]

Find the most recent successful review for this account in the run root.
Choose a new uniquely named run directory path; let the collector create
it during scanning. Never overwrite a prior run.
Scan the account, read the output, inspect accessible candidate media and
weaker comparators completely, and save a dated report with source post
identifiers. Keep organic strength and pursuit priority separate from readiness for
each proposed ad use. Give concrete reuse/edit/re-record directions,
including as-is viewing/profile-growth, existing warm-audience nurture,
and engagement/message-led
paths when appropriate. Match outcomes to each use and disclose attribution
gaps; do not treat account growth or likes as attributed follows or leads. Broaden a thin weekly comparison within
the permitted scope using the skill's representative baseline procedure.
Compare with the prior report: prioritize new relevant candidates and
meaningful changes in the recommendation or its supporting evidence.
Include a short unchanged/watchlist section. Do not regenerate already
delivered drafts unless the new evidence or my request warrants it.
Report access failures explicitly and retain the last successful review.
If nothing actionable changed, save a short status rather than repeating
the full report. Do not launch, boost, upload, message, or publish anything.
```

The user chooses cadence and notification behavior in the host. An automated report is not authorization to send an email, Slack, or Telegram message. A separate creative batch can be requested from a selected recommendation after review.

## Compare useful changes

Read the previous successful scan, analysis, and report, not merely the latest directory. Match by account and stable `post_id`/permalink; retain identifiers only in private outputs. Compare setup and coverage first: account, publication window, age cutoff, caps, exclusions, threshold, baseline method, and comparator count. Changed settings or a partial scan limit what can be inferred.

Classify findings in the report:

- **New candidate:** newly reviewed content with a relevant signal and a useful paid hypothesis. Content absent from the previous sample may be newly included because of age filters or caps, rather than newly published.
- **Changed recommendation:** new proof, better content access, a confirmed destination, a changed offer, or measured evidence changes priority, a proposed ad use, its readiness, or direction. State which changed, before/after, and why. Completing an asset review can improve readiness without changing priority.
- **New signal crossing:** a post now crosses a screening bar. Report both measurement ages and baseline changes; lifetime growth is not evidence of a fresh surge.
- **Unchanged/watchlist:** already reviewed and still useful; record what evidence or asset work is pending. Link the prior draft instead of producing it again.
- **Unavailable:** missing from the current scan, excluded, outside the window, inaccessible, or affected by an error. Absence is not a fall in performance.

Counts and multiples can change as posts age or the rolling baseline changes. Do not announce every numerical movement as actionable. Recommend a new action only when the evidence or business context changes the decision. Record a compact decision history in each private report: post identifier, organic strength, pursuit priority, proposed uses with per-use readiness/direction, supporting signal/reference window, inspected evidence, proposed adaptation/test, draft location if any, and pending item. For older reports with a generic hold, recover the underlying reason rather than assuming the post had low priority. Existing Markdown reports are sufficient; no database or new secret configuration is required.

## Unattended setup checks

Before enabling a requested schedule, perform one read-only run with the intended runtime and secret retrieval method. Use absolute paths, a private location the scheduler can read, and logs the user can inspect. On macOS, background jobs may be unable to read Documents/Desktop; choose a scheduler-accessible private location and Keychain-backed retrieval. Do not put tokens in scheduler arguments, prompt text, config files, or logs. Verify a real scheduled cycle before describing unattended execution as working.

If the host cannot inspect media unattended, explicitly offer a recurring metrics shortlist followed by a manual creative review. State that narrower coverage in the report.
