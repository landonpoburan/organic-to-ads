# Organic to Ads

Review Instagram posts, find performance outliers, and decide what deserves a Facebook or Instagram ad test. Optionally expand a selected post into hooks, ad concepts, copy, scripts, or related content.

Some of the best performing ads I run come from organic social media content. This skill reviews Instagram content for performance outliers, recommends which posts could become Facebook or Instagram ads, and explains what to keep or change. It can also expand a promising post into new hooks, ad concepts, copy, scripts, and related content.

## What you get

- A review that separates organic strength and candidate priority from readiness for each ad use: test as-is for relevant video views/audience building, adapt for enquiries or sales, or skip uses that do not fit.
- Outlier comparisons that show the metric, post value, baseline, multiple, and comparator count.
- A complete spoken/written review of accessible shortlisted creative, with visual checks, source-specific mechanisms, and explicit access gaps.
- Optional expansions that preserve the source idea while testing different creative approaches.
- A read-only Meta collector that scans a connected account's recent posts and available Insights automatically.
- An offline Python helper for CSV/JSON metrics and a local installer.
- A decision-first report with source-specific adaptations, production effort, and a practical first test.
- Opt-in weekly review guidance that tracks new candidates and changed decisions instead of repeating the same winners.

The package contains no ad-account IDs, credentials, client exports, private integrations, or tracking systems. It does not launch campaigns or boost posts.

## Requirements

Use an assistant that supports directory-based `SKILL.md` skills. The included setup steps cover Codex and Claude Code. The instructions are provider-neutral, but other hosts may have different installation rules.

**Python 3.9+** runs the installer, automatic scan, and metrics helper. All scripts use the standard library; no pip/npm packages or paid connector are required. Your assistant's normal account/subscription requirements still apply.

For **automatic scanning**, connect an Instagram Business or Creator account through your own authorized Meta app/token, using the Facebook Login API route. That account must be linked to a Facebook Page. Configure access once, then ask the assistant to scan your account or an authorized client's account. You do not need to select or upload individual posts first. The collector pulls recent content, captions, carousel media links, and available metrics, then calculates outlier candidates.

For **supplied-content reviews**, you can still provide screenshots, captions, transcripts, or exports without an API connection. An arbitrary public profile URL does not grant access to private Insights. This package contains no shared OAuth service or username-only scraper; each automatic-scan user brings their own Meta access. Media links are provided for the assistant to inspect with its available tools; video transcription is not bundled.

## Install

Download this repository as a ZIP from GitHub and extract it, or clone the repository. Open a terminal in the extracted repository. Review `install.py`, then choose an existing project where you want to use the skill.

### Codex

```sh
python3 install.py --target codex --project /path/to/your/project --dry-run
python3 install.py --target codex --project /path/to/your/project
```

This copies the skill to `<project>/.agents/skills/organic-to-ads/`. Start a fresh Codex session in that project and invoke `$organic-to-ads`. [Official Codex skill documentation](https://learn.chatgpt.com/docs/build-skills) explains local discovery.

### Claude Code

```sh
python3 install.py --target claude --project /path/to/your/project --dry-run
python3 install.py --target claude --project /path/to/your/project
```

This copies the skill to `<project>/.claude/skills/organic-to-ads/`. Start a fresh Claude Code session there and invoke `/organic-to-ads`. [Official Claude Code skill documentation](https://code.claude.com/docs/en/skills) describes project and personal locations.

### Custom or personal location

If you already know the skills directory your host uses, pass it explicitly:

```sh
python3 install.py --target claude --skills-dir "$HOME/.claude/skills"
```

For Codex, use `--target codex --skills-dir /path/to/your/configured/skills-directory`. Local configurations may differ; use the current official docs or your host's configured directory. You can also manually copy `skills/organic-to-ads/` into a recognized skills directory.

The installer copies only thirteen release resources, including the MIT license notice. It makes no network requests, reads no credentials, and changes no assistant settings. It refuses to overwrite an existing installation, including a symlink. To update, review the changed files and replace them intentionally. There is no automatic update or deletion step. The installer is optional; nothing is installed just by downloading this repo. Installing the skill does not configure Meta account access automatically.

## Connect an Instagram account once

Follow [Instagram setup](skills/organic-to-ads/references/instagram-setup.md) for account requirements, permissions, secure token handling, and connection checks.

1. Use your Meta app's supported API version and authorized token. The read workflow normally needs Instagram basic/Insights access plus appropriate Page read access. The setup guide links official instructions; no campaign-write permission is requested by default.
2. Copy [meta-config.example.json](skills/organic-to-ads/references/meta-config.example.json) to a private location outside this repository. Fill in the API version, Instagram professional user ID, and local account label. Keep tokens out of the config.
3. On macOS, retrieve the token through your Keychain-backed `get_secret` helper. On other systems, your secret manager can inject it into the process. Alternatively, run a command with `--prompt-token` in your own terminal to enter it invisibly for that run. Never paste it into assistant chat, a command argument, or a committed file.
4. From this repository, verify account and Insights access:

```sh
python3 skills/organic-to-ads/scripts/scan_instagram.py check \
  --config /path/to/private/meta-config.json
```

If you need the Instagram user ID, use the guide's `discover` command to list linked accounts visible to your token. Verify that `check` returns the intended username and `insights_verified=true`. The example config intentionally has no API-version or account-ID default; you must supply your own.

The assistant can then run the scan automatically when you ask it to review that account. You can also run it directly:

```sh
python3 skills/organic-to-ads/scripts/scan_instagram.py scan \
  --config /path/to/private/meta-config.json \
  --output-dir /path/to/private/new-run-directory
```

It saves `scan.json`, `posts.json`, and `analysis.json` outside the repository. Existing output directories are refused. Defaults cover a trailing 90-day publication window, exclude posts younger than 48 hours, and cap retrieval at 200 eligible posts or 20 media pages. Change these non-secret settings when needed; coverage limits and unavailable metrics are reported. Known promoted post IDs can be excluded in the config.

The collector is read-only. It sends tokens in an HTTPS header, rejects redirects, uses pagination cursors, and suppresses raw API error bodies. It does not publish content, boost posts, or make ad-account changes.

## Use it

### Automatically review a connected account

```text
Use organic-to-ads to scan my configured Instagram account.
Config: [path to my private non-secret config]
Save the scan to: [new private run directory]
Goal: [brand growth / qualified messages / leads / sales]
Offer: [what I sell or promote]
Audience: [who it is for]
Next step: [destination or message flow]
Go through the recent content, surface outlier candidates, explain why
they likely resonated, and recommend what to develop or test as an ad.
Separate priority from readiness. Complete the accessible shortlisted
videos/carousels, distinguish the actual content from caption boilerplate,
and give specific reuse/edit/re-record directions and a first test.
```

Add `$organic-to-ads` in Codex or `/organic-to-ads` in Claude Code for explicit invocation. A configured account scan does not require you to provide a post first. The assistant uses the scan output to choose which posts and weaker comparators to inspect. If it cannot open returned images or videos, it states that limit instead of claiming a full visual review.

### Review supplied posts or an accessible profile

```text
Use organic-to-ads to assess these Instagram posts for paid ads.
Profile: [profile URL or handle]
Goal: [brand growth / qualified messages / leads / sales]
Offer: [what I sell or promote]
Audience: [who it is for]
Next step: [destination or message flow]
Data: [attach screenshots, captions, transcripts, or Insights export]
Identify measurable outliers, explain what likely worked, and recommend
which posts to reuse, adapt, develop, or skip. Keep priority and readiness
separate and state specific adaptations and any missing evidence.
```

The assistant can also select the skill from a matching request when the host supports automatic discovery.

### Review one post without Insights

```text
Use organic-to-ads on this carousel and caption. I want qualified
messages about my offer. I do not have Insights or a baseline. Give me a
qualitative paid-use assessment and tell me which metrics would improve it.
```

This can assess the creative and offer fit. It cannot prove that the post is an outlier.

### Expand a selected post

```text
Expand the strongest recommended post into three distinct ad concepts:
a static image, a carousel, and a short video. Include the hook, proof,
offer bridge, CTA, and what each tests. Use only supported claims.
```

You can request only hooks, ready-to-review copy, video scripts, or follow-up organic posts instead. Expansion is optional; a review does not automatically generate a full campaign or render media.

Directions come from the source's specific mechanism: a real question can become an expert response, a demonstrated process can become a hands-on video, and a useful checklist can become a tutorial or resource preview. Each direction explains what to preserve, what changes, its proof, and the required production. When you ask for copy or scripts, you get drafts rather than only a list of ideas.

### Repeat the review weekly

Use your assistant host's scheduling feature or existing automation system to run the [weekly review prompt](skills/organic-to-ads/references/weekly-review.md). Supply your private config, output location, business context, and desired cadence. The skill compares against the previous successful report and prioritizes newly relevant posts, new evidence, and changed recommendations. It keeps a short watchlist and refers back to existing drafts.

Scheduling is opt-in. Downloading or installing this package creates no background job. The collector can run unattended with a configured secure secret store; the complete creative review also needs an assistant runtime and access to the media. Counts increasing as posts age are not automatically a fresh outlier. Check one actual scheduled cycle before relying on the workflow. The guide covers private output history, access failures, and macOS background-file access.

## Scope of the review

This skill identifies strong organic performance and assesses opportunities to use that content in ads, including video views and warm-audience building or adaptation for enquiries and sales. It does not independently validate sources or factual claims, fact-check the content, or assess alignment with Meta advertising policies. A recommendation is a creative testing opportunity, not a compliance review or a guarantee of platform approval or paid results. Any source validation, policy review, and rights checks remain separate from this skill's review.

## How recommendations work

A strong organic post can have multiple ad opportunities. For example, **High priority: test as-is for relevant video views and warm-audience building; recommend adding an in-video CTA for training enquiries.** Readiness is specific to each use. A missing CTA is an adaptation opportunity, not a reason to reject the post or require a full re-recording. The assistant recommends the smallest useful change and explains what to preserve. Viewing does not guarantee follower growth or conversions.

**Warm-audience nurture** is another use: show strong organic posts to people already familiar with the business to reinforce familiarity, trust, and ongoing visibility. This is different from building a warm audience or running a conversion-focused retargeting ad. A CTA is optional; relevant engagement and viewing can be the intended response. The review identifies the available audience from your context and does not treat engagement as proof that trust or sales increased.

Other options include **Instagram follower growth** (test the existing post as an ad directing to the profile) and **engagement/message-led attention or leads** (for example, “DM [keyword] for [resource]” tied to an actual response journey). A follow prompt or in-video DM CTA can be a small optional/advised edit rather than a full re-recording. The skill recommends these paths only when they fit the post and goal.

For profile growth, assess visits, attributed follows, cost per follow, and visit-to-follow conversion where measurable. For message-led leads, assess message starts, relevant resource requests, qualified leads, and cost per relevant result. Missing attribution stays explicit. Likes/comments do not establish lead quality, and a message journey may use manual follow-up or an existing automation; the skill does not create one automatically.

When you supply a goal, the review recommends a primary use and a useful alternative where warranted. Without a goal, it presents the viable options without forcing a sales or enquiry objective. Reviews start with a short Summary, followed by supporting Details. Missing creative access stays visible without erasing a promising candidate's priority.

The review names the actual opening, argument, proof, and close from the asset. A recurring introduction in a caption does not define the video's topic. Full spoken content or all slides are reviewed where accessible; visual inspection is reported separately from transcript coverage. Available browser or transcription tools may be used after dependency checks. Transcription is not bundled, and no tools or speech models are installed automatically.

A thin weekly screen can be compared with a broader representative same-format set, usually up to the existing 90-day default, within the user's permitted scope. The report shows which baseline it used and whether the signal persists. It never changes windows or methods merely to manufacture a winner. Lifetime measurement ages and unknown promoted status remain visible even with more comparators.

A first-test brief specifies the asset, source learning, production work, destination, constants, changed variable, and business outcome. Missing paid benchmarks produce an exploratory recommendation with clearly identified launch inputs; they do not stop useful creative development.

## Analyze exported metrics

Prepare a representative recent dataset using the [input schema](skills/organic-to-ads/references/data-input.md). Export the same measurement age for comparable posts where possible, such as 48 hours after publication. Do not mix different accounts, formats, known paid distribution, or measurement definitions.

```sh
python3 skills/organic-to-ads/scripts/analyze_posts.py examples/posts.csv
```

For your own data:

```sh
python3 skills/organic-to-ads/scripts/analyze_posts.py /path/to/posts.csv \
  --threshold 3 --baseline mean --min-comparators 5
```

Output is JSON on stdout. Keep private data and saved results outside this public repository. Give the result to your assistant with the actual posts and offer context.

The helper excludes each candidate from its own baseline, excludes known paid posts, and keeps missing metrics distinct from zero. Unknown distribution, unknown measurement age, or a thin sample produces provisional flags. Mean and median baselines are supported. A zero baseline produces no numerical multiple.

**3× and five comparators are configurable screening heuristics.** They are not universal account settings, statistical significance, or a promise of ad performance. The helper measures organic signals; the skill applies content and business judgment. An unrelated viral clip can still be a poor ad candidate.

Automatic live scans retrieve lifetime snapshots from posts of different ages and cannot reliably identify every boosted feed post. Those crossings are labeled **provisional outlier candidates**, with measurement ages and distribution limits visible. For matched-age comparisons, use an export with equal observation windows. You still get the scan, comparisons, and recommendations without manually choosing source posts.

## Try the fictional demo

Give your assistant [posts.csv](examples/posts.csv), [brief.md](examples/brief.md), and [source-content.md](examples/source-content.md). Ask it to recommend a first sales test and expand the selected post into three ad directions. The demo includes a measurable save outlier, a high-reach reel without a comparable baseline, and a known boosted post.

Read the [complete worked review](examples/worked-review.md) to see the intended level of output: decision table, baseline evidence, source mechanism, first test, and actual static copy, carousel sequence, and video script. The [evaluation cases and rubric](examples/evaluation.md) help check whether your own assistant delivers useful recommendations. The [shared-caption regression case](examples/shared-caption-case.md) tests whether it distinguishes a video's real subject from boilerplate and preserves priority while identifying necessary adaptations.

All examples are fictional. Written creative descriptions support a source-based exercise, not a claim that real media was viewed. For the partial-evidence case, omit the creative descriptions and check that the assistant keeps its visual assessment conditional.

## Privacy and publishing

Keep real exports, screenshots, reports, credentials, and local configuration outside this repo. `.gitignore` covers common accidental additions, but it cannot sanitize previously committed files. Review exactly what you stage before publishing. Install paths contain the user's own local directory; no author's private paths are required.

The skill recommends tests and drafts creative. Separate implementation checks may include asset rights, music eligibility, placements, and the current [Meta Advertising Standards](https://transparency.meta.com/policies/ad-standards/). Those checks are outside the skill's review scope.

To publish this package, upload the contents of this repository directory to your chosen GitHub repository. The ZIP includes the same source files. No Git history or user data is included. The code and instructions are provided under the MIT license.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Tests cover baseline arithmetic, paid exclusions, missing data, zero baselines, incomparable windows, malformed input, installation behavior, and mocked Meta retrieval/security behavior. No real credentials are used by the test suite. They do not substitute for a live connection check or paid test, or prove that every assistant will follow the instructions correctly.

The collector also passed a separate read-only connection check and bounded seven-day live scan on an authorized professional account on October 8, 2026, using Python 3.9 and Graph API v25.0. This checked secure token retrieval, account/media access, actual Insights, carousel-child retrieval, scoring, and private output files. A timestamp-format issue found in that run was fixed and covered by regression tests. Live credentials, account identifiers, and results are excluded from this repository. Each user's own account and permissions still need the setup guide's connection check.

For output quality, use the fictional evaluation prompts with your intended assistant and review its actual decisions and drafts. The included worked review is an authored reference, not an independent model evaluation.
