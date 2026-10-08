# Outliers and paid potential

## Comparable baselines

The unit is a post relative to this account's comparable posts, not an absolute viral threshold. Use a representative recent period; a trailing 90-day publication window is a useful starting point when supplied data supports it. Do not imply a seven-day sample is a 90-day history.

Group by account and format (reel, carousel, image, video). Group more narrowly by storytelling structure when enough comparable posts exist. Comparing a talking-head reel to a demonstration reel can reveal a format effect rather than a message effect. Keep observed performance windows equal: 48-hour insights should be compared with other 48-hour insights. Lifetime totals from differently aged posts are directional only. If observation windows are unavailable, disclose the limitation.

Exclude paid/boosted distribution, giveaways, collaborations, and unusual events where they materially distort the question. The helper excludes `paid=true`; other exclusions require the reviewer's judgment and must be explained. Unknown paid status stays unknown. Do not declare promotion based only on a likes/views ratio.

## Strengthen a thin weekly screen

A weekly scan can discover fresh candidates while having too few same-format comparators to support its magnitude. Separate the discovery window from the reference set:

1. Keep the original weekly signal and its comparator count visible.
2. If the user permits broader account review, collect one representative broader window, usually the existing 90-day default or a supplied 30/90-day history. Use the same account, format, metric definitions, baseline method, exclusions, and threshold. Do not override an expressly restricted review window.
3. Reassess the shortlisted posts using the broader run's own contemporaneous data. Do not splice older counts into a new snapshot or double-count posts present in both runs. Match by stable post identifier.
4. Report the reference window, comparator count, value, baseline, multiple, rate, and limits. If a crossing disappears, say so; commercial relevance can still justify developing the post. Do not select whichever window or method makes it look best.
5. Stop expanding once a representative permitted sample is obtained or available history/caps are exhausted. Retain the disclosed uncertainty instead of repeatedly fetching or manufacturing confidence.

More comparators do not fix lifetime age differences or unknown paid distribution. Prefer supplied matched-age measurements for strong organic claims. When those are unavailable, use rates and nearby-age contrasts as supporting diagnostics and keep live flags provisional. Missing comparison history affects evidence confidence; it does not by itself require discarding a promising creative.

## Arithmetic

For each post and each available metric:

```text
baseline = mean(metric on OTHER comparable posts)
multiple = post metric / baseline
```

Exclude the candidate from its own baseline. This matters for small samples: one strong post can inflate the average enough to hide itself. Report the number of other posts used for each metric, since missing metrics can change the denominator.

The helper supports `--baseline median` when skew makes a mean unstable. Choose and disclose one method; do not switch methods to manufacture a winner. A missing, empty, or zero baseline produces an unavailable multiple, never infinity. A zero baseline with new activity can be a qualitative change worth reviewing, without a numerical outlier claim.

The default **3×** threshold is a transparent screening choice, not a validated universal rule. Change it when the user's brief provides another bar. The helper labels fewer than five comparable observations as thin evidence. Five is also a configurable review heuristic, not statistical significance. Multiple comparisons increase the chance of chance flags: display each component, not just the maximum ratio.

Use:

- Counts: reach, views, saves, shares, comments, likes, total interactions, profile visits, follows, qualified messages, leads, or sales, when actually measured on the same basis.
- Rates: saves/reach, shares/reach, interactions/reach. Report percentages clearly.
- Goal-related signals: qualified questions, attributable messages/leads, and downstream results. Describe attribution limits.

The helper supports the standard count fields documented in `data-input.md` and the three reach-based rates. Additional business metrics can be reviewed manually with equally explicit definitions.

If `total_interactions` is supplied, use it without adding it to its components. Derive it from likes + comments + saves + shares only when all four exist, and label the derivation. Missing parts are not zero. Reach zero makes all reach-based rates unavailable. Views can include repeat viewing; do not call them unique reach.

## Interpret the signal

An engagement outlier is a reason to inspect the content. It is not an estimated probability of profitability. Report organic evidence confidence separately from commercial judgment.

- Strong counts plus strong rates support resonance better than counts alone.
- Shares/saves can reveal useful or identity-relevant material, but may come from people who will never buy.
- Comments asking about the actual offer are different from emoji reactions or keyword-entry comments. Cite actual wording without guessing personal attributes.
- A CTA asking for a comment can inflate the metric used to rank that post.
- Celebrity/status, timing, outside reposts, paid exposure, and collaboration can confound the result.
- A cold audience may need context that existing followers already have.

Use weaker comparable posts to challenge the explanation. If the same mechanism appears in both winners and losers, it is not sufficient on its own. A difference suggests a testable hypothesis, not proof of causation.

## Goal fit

For brand/account growth, judge relevant attention and the reason to visit/follow, not follower totals alone. For messages, judge whether the post creates a concrete conversation about the offer and whether a working message flow exists. For leads/sales, judge the creative offer bridge, proof presented in the source, and continuity with the destination. For relevant video views/awareness, a missing offer CTA does not rule out reuse; viewing and attention can be the primary outcome. Describe warm-audience building as a proposed follow-up journey, not guaranteed follower or lead growth. Translate an organic comment CTA only when the intended paid journey is known; do not assume every advertiser has a DM automation or free guide.

Keep measured performance, audience relevance, offer/CTA fit, and evidence confidence distinct. Derive pursuit priority from those judgments, then readiness and direction separately for each plausible ad use, without a pseudo-precise blended score. Explain what determines the paid direction and next action; do not turn unfinished asset inspection into an unsupported negative judgment.


### Match outcomes to growth and engagement uses

For follower growth, assess an existing-asset test directing to the Instagram profile. An offer CTA is unnecessary; a follow prompt may be an optional variant. Assess profile visits, attributed follows, cost per follow, and visit-to-follow conversion where those data are available. Do not attribute all account growth to the ad when attribution is missing.

For engagement, distinguish relevant attention from a message-led lead journey. A DM-keyword/resource CTA can connect interaction to enquiries when the actual resource and response flow are known. Manual follow-up is an option; automation is not assumed. Assess relevant engagement for attention, or message starts, resource requests, qualified leads, and cost per relevant result for lead generation. Do not turn incentivized comments, likes, or unqualified messages into qualified leads.


### Existing warm-audience nurture

Distinguish distributing strong organic content to an existing warm audience from using viewing/engagement to build one. Relevant educational, perspective, or story content may support ongoing familiarity and visibility without an offer CTA. Recommend reuse when the asset already serves that purpose. Name the available audience only from supplied context, and assess relevant engagement/viewing as response measures. Do not equate them with proven trust, leads, or sales. Do not import universal budgets, frequency, or timing from the author's private strategy notes.
