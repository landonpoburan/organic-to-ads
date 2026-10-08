# Automatic Instagram scan setup

Use this route to scan recent content and identify outlier candidates without asking the user to select posts. It restores the Meta API route used by the original monitoring workflow. All requests are read-only HTTP GET requests. It does not boost posts or use an ad account.

## Account access

This collector uses **Instagram API with Facebook Login**, at `graph.facebook.com`. It needs a Business or Creator Instagram account linked to a Facebook Page, a Meta app configured for that API, and a token authorized for that account/Page. It is not a username-only scraper, a shared OAuth app, or a route to arbitrary profiles' private Insights.

Use the user's existing authorized token/app when available. For a new setup, follow the official [Instagram API with Facebook Login overview](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/) and [Insights guide](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/insights/). Meta also publishes an [Instagram API collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api). Product labels and permission prerequisites can change; use the current app dashboard and official guides.

The read workflow normally needs `instagram_basic`, `instagram_manage_insights`, and `pages_read_engagement`. `pages_show_list` is used by linked-Page discovery. Page/business assignments and any additional prerequisites depend on the user's token and app setup. Do not request publishing or campaign-write permissions as a default. A token with only `ads_read` is not sufficient for organic Instagram Insights.

The user brings their own Meta app/access. Using a shared app for accounts outside its permitted development roles can require Meta review/approved permissions; this repository does not supply that shared service. Generate or renew the appropriate access token using the user's Meta app setup or [Graph API Explorer](https://developers.facebook.com/tools/explorer/). Never ask the user to paste a token into the assistant conversation.

## Credentials

Credentials stay outside this repository and the config file. There is no token CLI argument, dotenv loader, or credential-file input.

- **macOS:** store the token in Keychain using the user's `set_secret` tool and retrieve it through `get_secret`. The script finds `get_secret` on PATH and calls it with `token_secret_name`. It never reads a secret from a Documents file or invokes `security` directly. If no helper is installed, the user can run the hidden prompt below in their own terminal for a one-time session.
- **Other systems:** let the user's secret manager inject the variable named by `token_secret_name` into the process. Do not write it into this repo or a dotenv file.
- **Interactive alternative:** append `--prompt-token` to `discover`, `check`, or `scan`. The user enters the token into a hidden terminal prompt. It stays in memory for that run; it is not stored. This option requires an interactive terminal and should be run by the user, not by asking for the token in chat.

When a `get_secret` helper exists but fails, the scan stops. It does not silently fall back to a different token source. If using several apps/accounts, set a different non-secret credential name per config.

The token is sent only in the HTTPS authorization header. Pagination uses returned cursors rather than token-bearing `paging.next` URLs. Redirects are rejected and upstream error bodies are not printed. The script rejects any response containing its token before printing or saving it.

## Configure once

1. Check `python3 --version` reports Python 3.9 or later. No pip/npm dependencies are needed.
2. Copy [meta-config.example.json](meta-config.example.json) to a private config location **outside this repository and installed skill**, such as an application config directory. Keep only its documented non-secret fields.
3. Set `api_version` to a supported version from the Meta app dashboard, such as the version used by the user's existing integration. The example intentionally has no version default; it must be configured explicitly.
4. Set `instagram_user_id` to the Instagram professional user ID, not an ad-account ID, Facebook Page ID, profile URL, or handle. Set `account_label` to a recognizable local name.
5. Securely configure the token as above, then test access.

If the user needs to find the Instagram user ID, run linked-Page discovery with the version they selected. Replace `vNN.N` below with that actual version before running:

```sh
python3 <skill-directory>/scripts/scan_instagram.py discover --api-version vNN.N
```

Discovery returns accounts visible to that token, with Page names and Instagram IDs/usernames. Use those results locally; do not commit them. An empty list can indicate missing Page permissions or business assignments. For an existing system-user token, the ID may instead already be in the user's own integration; discovery need not enumerate every assigned asset.

Then run:

```sh
python3 <skill-directory>/scripts/scan_instagram.py check --config <private-config.json>
```

Verify the returned username. `insights_verified=true` means a read of an actual media reach insight succeeded. If no suitable sample returns reach, the result says Insights access is unverified; do not treat that as confirmed permission. Expired tokens or denied requests fail with a credential-free diagnostic.

## Scan and review

Choose a **new** private run directory outside the repo/installed skill. Existing directories are refused to protect earlier scans.

```sh
python3 <skill-directory>/scripts/scan_instagram.py scan \
  --config <private-config.json> --output-dir <new-private-run-directory>
```

The defaults select posts published in the trailing 90 days, exclude posts younger than 48 hours, and cap retrieval at 200 eligible posts or 20 media pages. These are configurable screening settings, not account benchmarks. The API may return more old posts while paginating; date filtering is performed locally. Any retrieval cap is explicitly reported.

The scan saves:

- `scan.json`: account identity, publication window, coverage/exclusions/warnings, full post content records, and analysis.
- `posts.json`: captions, source links, metrics, parent-media links, and every retrieved carousel child-media link.
- `analysis.json`: leave-one-out baseline comparisons and outlier candidates from the bundled analyzer.

The private run directory and files are created with restrictive permissions on systems that support them. No raw API response or token is saved. API errors fail the run instead of returning fake zeros or claiming no winners. Transient failures get up to three attempts with short backoff; there is no unlimited retry loop.

The assistant reads these files, surfaces candidate outliers with their value/baseline/multiple, inspects the actual accessible content, assesses relevant ad opportunities, and gives readiness plus test/adapt/skip direction for each use. The user can supply goal, offer, and audience context; without a goal, the assistant presents viable options rather than forcing a conversion objective; they do not need to pick the source post first. Media URLs can expire, so inspect them during the same review. No image downloader, renderer, or video-transcription service is bundled; use available tools and disclose incomplete creative access.

## Data limits

Current media Insights are lifetime snapshots. `measurement_age_hours` shows each post's actual age; the scanner does **not** pretend these are matched 48-hour snapshots. Numeric crossings are surfaced as **provisional outlier candidates** because observation ages differ and promoted feed posts are not reliably detectable. `media_product_type=AD` is excluded, but that alone cannot certify organic distribution. Add known boosted or otherwise unsuitable post IDs to `exclude_post_ids`.

The script tries reach, views, saved, shares, and total interactions; likes and comments come from the media node. Only recognized explicit unsupported-metric errors (code 100, no nonzero subcode, and an accepted error type) trigger a single round of individual metric requests. Recognized unsupported metrics remain unavailable rather than zero. Unknown code-100 errors and other retrieval failures stop the run with a sanitized diagnostic, including failures during individual requests. Unrecognized metric-rejection wording also stops the run conservatively. It supports single-value `values` and `total_value` responses. Permissions/rate-limit/token failures are not downgraded to unavailable metrics. Metric availability depends on API version, media type, age, and access. No absent metric is assigned zero.

For more rigorous comparisons, provide an export with equal observation windows through the original CSV/JSON route. A connected scan remains useful for selecting what to inspect, but it does not prove paid profitability or a creative's eligibility.
