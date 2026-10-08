#!/usr/bin/env python3
"""Read an authorized Instagram professional account through Meta's Facebook Login API."""

import argparse
import datetime as dt
import getpass
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from analyze_posts import analyze, normalize

UTC = dt.timezone.utc
METRICS = ("reach", "views", "saved", "shares", "total_interactions")
MEDIA_FIELDS = "id,caption,media_type,media_product_type,permalink,timestamp,media_url,thumbnail_url,like_count,comments_count"
CONFIG_KEYS = {
    "api_version", "instagram_user_id", "account_label", "token_secret_name",
    "lookback_days", "min_age_hours", "max_posts", "max_pages", "exclude_post_ids",
    "outlier_threshold", "baseline", "min_comparators",
}


class ScanError(Exception):
    pass


class GraphError(ScanError):
    def __init__(self, code=None, status=None, transient=False, subcode=None,
                 error_type=None, unsupported_metric=False):
        self.code = code if type(code) is int else None
        self.status, self.transient = status, transient
        self.subcode = subcode if type(subcode) is int else None
        self.error_type = error_type if isinstance(error_type, str) and error_type in {"OAuthException", "GraphMethodException"} else None
        self.unsupported_metric = bool(unsupported_metric) and self.code == 100 and self.subcode in {None, 0}
        if code == 190:
            message = "Meta access token is invalid or expired. Renew it in your credential store."
        elif code in {10, 200}:
            message = "Meta denied access. Check account/Page assignments and read/Insights permissions."
        elif code == 100:
            message = "Meta rejected an ID, field, or metric. Check the configured account and API version."
        elif status == 429 or code in {4, 17, 32, 613}:
            message = "Meta rate limit reached. Retry later or reduce the scan size."
        else:
            message = "Meta request failed. Check account access, network availability, and supported API version."
        # Never echo response bodies, URLs, headers, tokens, or exception text.
        super().__init__(message)


def unsupported_metric_error(error):
    """Classify only explicit metric rejections; retain no upstream message."""
    subcode, error_type = error.get("error_subcode"), error.get("type")
    if error.get("code") != 100 or (subcode is not None and (type(subcode) is not int or subcode != 0)):
        return False
    if error_type is not None and error_type != "OAuthException":
        return False
    message = error.get("message")
    if not isinstance(message, str):
        return False
    # Unknown ID/field/access failures must remain failures, even with code 100.
    return bool(re.search(
        r"(?:metric(?:s)?\s+must be one of|"
        r"value must be a valid insights metric|"
        r"(?:insights?\s+)?metric\s+(?:['\"]?[a-z_]+['\"]?\s+)?"
        r"(?:is |are )?not supported(?:\b)|"
        r"(?:insights?\s+)?metric\s+(?:['\"]?[a-z_]+['\"]?\s+)?"
        r"(?:is |are )?unsupported(?:\b))",
        message, re.IGNORECASE))


def api_version(value):
    if not isinstance(value, str) or not re.fullmatch(r"v[1-9]\d*\.\d+", value):
        raise ScanError("Set api_version to a supported version from your Meta app dashboard, in vNN.N form.")
    return value


def node_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+", value):
        raise ScanError("Instagram user and media IDs must be numeric strings; ad-account IDs and handles are not valid here.")
    return value


def read_config(path):
    try:
        with path.open(encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, ValueError, UnicodeError):
        raise ScanError("Cannot read the non-secret JSON config. Check its path and JSON syntax.") from None
    if not isinstance(config, dict) or set(config) - CONFIG_KEYS:
        raise ScanError("Config must contain only documented non-secret fields. Never put tokens or credential paths in it.")
    config["api_version"] = api_version(config.get("api_version"))
    config["instagram_user_id"] = node_id(config.get("instagram_user_id"))
    label = config.get("account_label")
    if not isinstance(label, str) or not label.strip():
        raise ScanError("Set account_label to a nonempty local label.")
    config["account_label"] = label.strip()
    secret_name = config.setdefault("token_secret_name", "META_ACCESS_TOKEN")
    if not isinstance(secret_name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", secret_name):
        raise ScanError("token_secret_name must be a credential name, not a token or path.")
    for key, default, low, high in [
        ("lookback_days", 90, 1, 365), ("max_posts", 200, 1, 1000),
        ("max_pages", 20, 1, 100), ("min_comparators", 5, 2, 1000),
    ]:
        value = config.setdefault(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ScanError(f"{key} must be an integer between {low} and {high}.")
    for key, default, low in [("min_age_hours", 48, 0), ("outlier_threshold", 3, 1)]:
        value = config.setdefault(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < low:
            raise ScanError(f"{key} must be a finite number of at least {low}.")
    if config["outlier_threshold"] <= 1:
        raise ScanError("outlier_threshold must be greater than 1.")
    if config["min_age_hours"] >= config["lookback_days"] * 24:
        raise ScanError("min_age_hours must leave a nonempty publication window within lookback_days.")
    baseline = config.setdefault("baseline", "mean")
    if not isinstance(baseline, str) or baseline not in {"mean", "median"}:
        raise ScanError("baseline must be mean or median.")
    excludes = config.setdefault("exclude_post_ids", [])
    if not isinstance(excludes, list):
        raise ScanError("exclude_post_ids must be a list of numeric post-ID strings.")
    for value in excludes:
        node_id(value)
    return config


def load_token(secret_name, prompt=False):
    if prompt:
        if not sys.stdin.isatty():
            raise ScanError("The hidden token prompt requires an interactive terminal.")
        token = getpass.getpass("Meta token (hidden; kept in memory for this run): ").strip()
    else:
        # macOS users can use their existing Keychain get_secret helper.
        helper = shutil.which("get_secret")
        if helper:
            try:
                result = subprocess.run([helper, secret_name], capture_output=True, text=True, timeout=15)
            except (OSError, subprocess.TimeoutExpired):
                raise ScanError("get_secret failed. Check the credential helper outside this scan.") from None
            if result.returncode:
                raise ScanError("get_secret could not retrieve the requested credential. Store it securely before retrying.")
            token = result.stdout.strip()
        else:
            if sys.platform == "darwin":
                raise ScanError("Use a Keychain-backed get_secret helper on macOS, or run --prompt-token in your own terminal.")
            # For other systems, a secret manager may inject the variable into the process.
            # No dotenv or credential file is read.
            token = os.environ.get(secret_name, "").strip()
    if not token or re.search(r"[\s\x00-\x1f\x7f]", token):
        raise ScanError("No valid token was supplied. Use your credential store or the hidden terminal prompt.")
    return token


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ScanError("Refusing an API redirect to keep authorization on the configured Meta host.")


class GraphClient:
    def __init__(self, version, token, opener=None, sleep=time.sleep):
        self.version = api_version(version)
        self.token = token
        self.opener = opener or urllib.request.build_opener(NoRedirect())
        self.sleep = sleep

    def get(self, path, params=None):
        if not re.fullmatch(r"(?:me/accounts|\d+(?:/(?:media|insights|children))?)", path):
            raise ScanError("Unsupported read-only Graph endpoint.")
        if params and "access_token" in params:
            raise ScanError("Tokens must be sent in the authorization header only.")
        query = urllib.parse.urlencode(params or {})
        url = f"https://graph.facebook.com/{self.version}/{path}" + (f"?{query}" if query else "")
        if self.token in url:
            raise ScanError("Refusing a request containing the credential in its URL.")
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"}, method="GET")
        for attempt in range(3):
            status = None
            try:
                with self.opener.open(request, timeout=30) as response:
                    payload = response.read(16 * 1024 * 1024 + 1)
            except urllib.error.HTTPError as error:
                status = error.code
                payload = error.read(16 * 1024 * 1024 + 1)
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt < 2:
                    self.sleep(2 ** attempt)
                    continue
                raise ScanError("Network request failed after three attempts. No API error details or credentials were logged.") from None
            if len(payload) > 16 * 1024 * 1024:
                raise ScanError("Meta response exceeded the supported size.")
            try:
                data = json.loads(payload)
            except (ValueError, UnicodeError):
                if status in {429, 500, 502, 503, 504} and attempt < 2:
                    self.sleep(2 ** attempt)
                    continue
                raise GraphError(status=status) from None
            if not isinstance(data, dict):
                raise ScanError("Meta returned an unexpected response shape.")
            error = data.get("error")
            if error or status is not None:
                error = error if isinstance(error, dict) else {}
                code = error.get("code")
                transient = bool(error.get("is_transient")) or code in {4, 17, 32, 613} or status in {429, 500, 502, 503, 504}
                if transient and attempt < 2:
                    self.sleep(2 ** attempt)
                    continue
                raise GraphError(code=code, status=status, transient=transient,
                                 subcode=error.get("error_subcode"), error_type=error.get("type"),
                                 unsupported_metric=unsupported_metric_error(error))
            return data


def pages(client, path, params, max_pages):
    """Use cursor values only. Never follow paging.next URLs carrying tokens."""
    current, seen = dict(params), set()
    for index in range(max_pages):
        payload = client.get(path, current)
        data = payload.get("data")
        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise ScanError("Meta list response is incomplete or malformed.")
        paging = payload.get("paging") or {}
        if not isinstance(paging, dict):
            raise ScanError("Meta pagination response is malformed.")
        has_next = bool(paging.get("next"))
        cursors = paging.get("cursors") or {}
        after = cursors.get("after") if isinstance(cursors, dict) else None
        if has_next and (not isinstance(after, str) or not after or after in seen):
            raise ScanError("Meta pagination could not be completed safely.")
        yield data, has_next and index == max_pages - 1
        if not has_next:
            return
        seen.add(after)
        current["after"] = after


def identity(client, instagram_id):
    result = client.get(node_id(instagram_id), {"fields": "id,username,followers_count,media_count"})
    if not isinstance(result.get("username"), str) or not result["username"]:
        raise ScanError("Meta did not return the configured Instagram professional account.")
    return {key: result.get(key) for key in ("id", "username", "followers_count", "media_count")}


def count_value(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 0 or int(value) != value:
        return None
    return int(value)


def insight_values(payload):
    data = payload.get("data")
    if not isinstance(data, list):
        raise ScanError("Meta Insights response is malformed; no results were assumed to be zero.")
    values = {}
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        points = item.get("values")
        value = None
        if isinstance(points, list) and len(points) == 1 and isinstance(points[0], dict):
            value = count_value(points[0].get("value"))
        total = item.get("total_value")
        if value is None and isinstance(total, dict):
            value = count_value(total.get("value"))
        if value is not None:
            values[item["name"]] = value
    return values


def media_insights(client, media_id, metrics=METRICS):
    try:
        values = insight_values(client.get(f"{node_id(media_id)}/insights", {"metric": ",".join(metrics)}))
    except GraphError as error:
        if not error.unsupported_metric:
            raise
        # One unsupported metric can reject the whole batch. Isolate it once.
        values = {}
        for metric in metrics:
            try:
                values.update(insight_values(client.get(f"{media_id}/insights", {"metric": metric})))
            except GraphError as individual_error:
                if not individual_error.unsupported_metric:
                    raise
    return values, [metric for metric in metrics if metric not in values]


def check_access(client, config):
    account = identity(client, config["instagram_user_id"])
    sample = client.get(f"{config['instagram_user_id']}/media", {"fields": "id,media_product_type", "limit": 10})
    if not isinstance(sample.get("data"), list):
        raise ScanError("Cannot verify media read access.")
    checked = False
    for row in sample["data"]:
        if isinstance(row, dict) and row.get("media_product_type") not in {"STORY", "AD"}:
            values, _ = media_insights(client, node_id(row.get("id")), ("reach",))
            checked = "reach" in values
            if checked:
                break
    return {"account": account, "media_read_access": True, "insights_verified": checked,
            "note": "Read operations succeeded." if checked else "No suitable reach insight returned; Insights access is not verified."}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    # Meta uses compact offsets (+0000). Python 3.9's fromisoformat needs
    # colon-separated offsets; normalize without dropping timezone information.
    normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", value.replace("Z", "+00:00"))
    parsed = dt.datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timezone missing")
    return parsed.astimezone(UTC)


def collect(client, config, now=None):
    now = now or dt.datetime.now(UTC)
    account = identity(client, config["instagram_user_id"])
    since = now - dt.timedelta(days=config["lookback_days"])
    latest = now - dt.timedelta(hours=config["min_age_hours"])
    posts, exclusions, warnings, seen = [], [], [], set()
    truncated = False
    valid_timestamps, invalid_timestamps = 0, 0
    for batch, page_limit in pages(client, f"{config['instagram_user_id']}/media",
                                   {"fields": MEDIA_FIELDS, "limit": 50}, config["max_pages"]):
        truncated = truncated or page_limit
        for index, item in enumerate(batch):
            media_id = node_id(item.get("id"))
            if media_id in seen:
                continue
            seen.add(media_id)
            try:
                posted = timestamp(item.get("timestamp"))
            except (ValueError, OverflowError):
                invalid_timestamps += 1
                exclusions.append({"post_id": media_id, "reason": "missing or invalid publication timestamp"})
                continue
            valid_timestamps += 1
            if not since <= posted <= latest:
                exclusions.append({"post_id": media_id, "reason": "outside selected publication/age window"})
                continue
            product, media_type = item.get("media_product_type"), item.get("media_type")
            if product in {"STORY", "AD"} or media_id in config["exclude_post_ids"]:
                exclusions.append({"post_id": media_id, "reason": "story, ad, or user-excluded post"})
                continue
            format_name = ("reel" if product == "REELS" else
                           {"IMAGE": "image", "CAROUSEL_ALBUM": "carousel", "VIDEO": "video"}.get(media_type))
            if not format_name:
                exclusions.append({"post_id": media_id, "reason": "unsupported media format"})
                continue
            metrics, missing_metrics = media_insights(client, media_id)
            children, children_truncated = [], False
            if format_name == "carousel":
                for child_batch, limited in pages(client, f"{media_id}/children",
                                                  {"fields": "id,media_type,media_url,thumbnail_url", "limit": 50}, config["max_pages"]):
                    children.extend({key: child.get(key) for key in ("id", "media_type", "media_url", "thumbnail_url")} for child in child_batch)
                    children_truncated = children_truncated or limited
            if children_truncated:
                warnings.append(f"Carousel {media_id}: child-media pagination limit reached; visual coverage is incomplete.")
            post = {
                "post_id": media_id, "account": config["account_label"], "format": format_name,
                "url": item.get("permalink") or "", "caption": item.get("caption") or "",
                "posted_at": posted.isoformat(), "retrieved_at": now.isoformat(),
                "measurement_age_hours": round((now - posted).total_seconds() / 3600, 2),
                "observation_window_hours": None, "paid": None,
                "likes": count_value(item.get("like_count")), "comments": count_value(item.get("comments_count")),
                "media_url": item.get("media_url"), "thumbnail_url": item.get("thumbnail_url"),
                "children": children, "missing_insight_metrics": missing_metrics,
                "visual_coverage_incomplete": children_truncated,
            }
            for field in ("reach", "views", "shares", "total_interactions"):
                post[field] = metrics.get(field)
            post["saves"] = metrics.get("saved")
            posts.append(post)
            if len(posts) >= config["max_posts"]:
                # Explicitly disclose a bounded scan even if the cap hits the last item.
                truncated = True
                break
        if len(posts) >= config["max_posts"]:
            break
    if seen and not valid_timestamps:
        raise ScanError("No readable publication timestamps were returned. Cannot determine which posts belong in the window.")
    if invalid_timestamps:
        warnings.append(f"{invalid_timestamps} posts excluded due to missing or invalid publication timestamps; coverage is incomplete.")
    if truncated:
        warnings.append("Media scan limit reached. Results cover only retrieved posts; increase the configured caps for more coverage.")
    warnings.extend([
        "Live Insights are lifetime snapshots from posts of different ages; multiples are directional screening signals.",
        "Boosted feed posts cannot reliably be detected from these fields. Known promoted posts must be supplied in exclude_post_ids.",
        "Media URLs can expire. Inspect them promptly; captions alone do not establish visual or video mechanics.",
    ])
    scores = (analyze(normalize(posts), config["outlier_threshold"], config["baseline"], config["min_comparators"])
              if posts else {"posts": [], "input_count": 0, "analyzed_count": 0, "excluded": [],
                             "meaning": "No eligible posts were retrieved in the selected publication/age window."})
    return {"schema_version": 1, "account": account, "retrieved_at": now.isoformat(),
            "window": {"published_since": since.isoformat(), "published_until": latest.isoformat(),
                       "lookback_days": config["lookback_days"], "min_age_hours": config["min_age_hours"]},
            "coverage": {"unique_media_seen": len(seen), "eligible_posts": len(posts),
                         "truncated": truncated, "exclusions": exclusions},
            "warnings": warnings, "posts": posts, "analysis": scores}


def discover(client):
    accounts, limited = [], False
    for batch, capped in pages(client, "me/accounts", {"fields": "id,name,instagram_business_account{id,username}", "limit": 50}, 20):
        limited = limited or capped
        for page in batch:
            instagram = page.get("instagram_business_account")
            if isinstance(instagram, dict):
                accounts.append({"page_name": page.get("name"), "page_id": page.get("id"),
                                 "instagram_user_id": instagram.get("id"), "username": instagram.get("username")})
    return {"accounts": accounts, "truncated": limited,
            "note": "These are the linked accounts visible to this token. Empty results can mean missing Page permissions or assignments; they do not prove no account exists."}


def validate_output(output):
    # Never write user data into an installed skill or a public release directory.
    if output.expanduser().is_symlink():
        raise ScanError("Choose a new output directory, not a symlink.")
    output = output.expanduser().resolve()
    skill = Path(__file__).resolve().parent.parent
    ancestors = [output, *output.parents]
    if skill == output or skill in output.parents or any((p / "skills/organic-to-ads/SKILL.md").is_file() for p in ancestors):
        raise ScanError("Choose an output directory outside the installed skill and public repository.")
    if output.exists():
        raise ScanError("Output directory already exists. Choose a new dated run directory; existing reports are not overwritten.")
    return output


def write_bundle(bundle, output):
    output = validate_output(output)
    try:
        output.mkdir(parents=True, mode=0o700, exist_ok=False)
        for name, value in [("scan.json", bundle), ("posts.json", bundle["posts"]), ("analysis.json", bundle["analysis"])]:
            with (output / name).open("x", encoding="utf-8") as handle:
                os.chmod(output / name, 0o600)
                json.dump(value, handle, indent=2, allow_nan=False)
                handle.write("\n")
    except OSError:
        raise ScanError("Could not save the scan. The chosen output directory may contain a partial copy; inspect it before retrying.") from None
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "scan"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, required=True, help="non-secret JSON config")
        command.add_argument("--prompt-token", action="store_true", help="hidden interactive token prompt; never put a token in arguments")
        if name == "scan":
            command.add_argument("--output-dir", type=Path, required=True, help="new private run directory outside this package")
    command = commands.add_parser("discover")
    command.add_argument("--api-version", required=True)
    command.add_argument("--secret-name", default="META_ACCESS_TOKEN")
    command.add_argument("--prompt-token", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "discover":
            version = api_version(args.api_version)
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", args.secret_name):
                raise ScanError("Use a credential name for --secret-name, not the credential itself.")
            client = GraphClient(version, load_token(args.secret_name, args.prompt_token))
            result = discover(client)
        else:
            config = read_config(args.config)
            if args.command == "scan":
                validate_output(args.output_dir)
            client = GraphClient(config["api_version"], load_token(config["token_secret_name"], args.prompt_token))
            if args.command == "check":
                result = check_access(client, config)
            else:
                bundle = collect(client, config)
                # Refuse accidental persistence if a malformed upstream payload echoed the token.
                serialized = json.dumps(bundle, allow_nan=False)
                if client.token in serialized:
                    raise ScanError("Refusing to save a response containing the credential.")
                output = write_bundle(bundle, args.output_dir)
                result = {"output_directory": str(output), "posts_scanned": len(bundle["posts"]),
                          "outlier_candidates": sum(p["outlier_flag"] or p["provisional_flag"] for p in bundle["analysis"]["posts"]),
                          "coverage_truncated": bundle["coverage"]["truncated"], "warnings": bundle["warnings"]}
        if client.token in json.dumps(result, allow_nan=False):
            raise ScanError("Refusing to print a response containing the credential.")
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ScanError, ValueError, OverflowError, OSError) as error:
        # Every ScanError has a fixed, credential-free explanation. Other exceptions
        # are deliberately opaque because upstream data may contain arbitrary text.
        print(f"Cannot scan: {error}" if isinstance(error, ScanError) else "Cannot scan: response data could not be processed safely.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
