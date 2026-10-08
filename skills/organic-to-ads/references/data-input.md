# Post data

The optional analyzer accepts UTF-8 CSV or a JSON array of objects. It uses only the Python standard library. It never connects to Instagram or reads credentials.

For an automatic connected-account scan, use `scripts/scan_instagram.py` as described in [instagram-setup.md](instagram-setup.md). Its `posts.json` is accepted directly by the analyzer, and `analysis.json` is already calculated. The scanner also retains captions, publication/retrieval timestamps, measurement ages, and media/child-media links for the assistant's creative review. Live scans use lifetime metrics and leave `observation_window_hours` and `paid` unknown, so their crossings are explicitly provisional. The user may exclude known promoted post IDs in the non-secret config.

## Required fields

| Field | Meaning |
|---|---|
| `post_id` | A local label or user-supplied post identifier. Unique within an account. |
| `account` | A local account label. Keep different accounts separate. |
| `format` | `reel`, `carousel`, `image`, or `video`. |

## Optional fields

| Field | Meaning |
|---|---|
| `url`, `caption` | Source link and actual caption, for the assistant's content review. |
| `paid` | `true`/`false`; blank means unknown. Known paid posts are excluded. |
| `observation_window_hours` | Positive number of hours after publication when these metrics were measured. Blank means unknown or incomparable lifetime totals. |
| `reach`, `views`, `likes`, `comments`, `saves`, `shares`, `total_interactions`, `profile_visits`, `follows` | Nonnegative measured counts. Blank/null means unavailable; `0` means measured zero. |

Counts must be whole numbers without commas, percent signs, or abbreviations. JSON counts can be numbers; empty CSV cells and JSON null are missing. `saved` is accepted as an alias for `saves`; conflicting values are rejected. Boolean JSON `paid` values and CSV `true`/`false`, `yes`/`no`, or `1`/`0` are supported. Unrecognized paid values fail rather than silently entering the baseline.

Choose the publication period in your export before analyzing; the helper does not fetch history or infer a date window. Keep the file representative and document exclusions. The helper groups by account, format, and observation window. It cannot verify that the supplied measurements actually have the same age or definition. An omitted observation window creates an exploratory group with a warning, not comparable verified evidence. Different known windows are never pooled.

Use `--threshold 3`, `--baseline mean` or `median`, and `--min-comparators 5` to change screening heuristics. An apparent crossing with thin counts, unknown paid status in the metric's comparison set, or unknown observation window is **provisional**. `outlier_flag=true` requires at least one crossing with adequate comparator count, known organic distribution, and a known matching observation window. This is a data-quality screen, not statistical significance or evidence of paid profitability. Unknown paid status in unrelated accounts/formats or posts without that metric does not downgrade an otherwise comparable metric.

The JSON result includes the exclusions, warnings, every supported metric comparison, the driving comparison, and an outlier/provisional flag. Rates are decimals: `0.05` means 5%. Do not describe the analyzer's `outlier_flag` as an ad recommendation. Creative and business judgment require the actual content and offer.

## Example

The repository's `examples/posts.csv` is entirely fictional. Run:

```sh
python3 skills/organic-to-ads/scripts/analyze_posts.py examples/posts.csv
```

The demo's `post-07` has 60 saves against a leave-one-out mean of 10, or 6×, with six comparators. The helper should flag it for inspection. `post-08` has no offer connection in the fictional brief; it demonstrates that an attention outlier can still be a poor sales-ad candidate. `post-09` is known paid and excluded. Unknown metrics stay null.
