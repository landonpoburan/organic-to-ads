#!/usr/bin/env python3
"""Offline organic performance screening. No network or credential access."""

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

COUNTS = (
    "reach", "views", "likes", "comments", "saves", "shares",
    "total_interactions", "profile_visits", "follows",
)
RATES = {"save_rate": "saves", "share_rate": "shares",
         "engagement_rate": "total_interactions"}
FORMATS = {"reel", "carousel", "image", "video"}


def missing(value):
    return value is None or (isinstance(value, str) and not value.strip())


def number(value, field, integer=False, positive=False):
    if missing(value):
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"{field} must be a number or empty")
    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise ValueError(f"{field} must be a plain number") from None
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError(f"{field} must be finite and {'positive' if positive else 'nonnegative'}")
    if integer and not result.is_integer():
        raise ValueError(f"{field} must be a whole count")
    return int(result) if integer else result


def paid_status(value):
    if missing(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int)):
        normalized = str(value).strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    raise ValueError("paid must be true, false, or empty")


def normalize(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("input must contain a nonempty list of posts")
    posts, seen = [], set()
    for position, raw in enumerate(rows, 1):
        try:
            if not isinstance(raw, dict):
                raise ValueError("each post must be an object")
            post = {}
            for field in ("post_id", "account", "format"):
                value = raw.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{field} is required as text")
                post[field] = value.strip()
            post["format"] = post["format"].lower()
            if post["format"] not in FORMATS:
                raise ValueError("format must be reel, carousel, image, or video")
            key = (post["account"], post["post_id"])
            if key in seen:
                raise ValueError("duplicate post_id within an account")
            seen.add(key)
            post["paid"] = paid_status(raw.get("paid"))
            post["observation_window_hours"] = number(
                raw.get("observation_window_hours"), "observation_window_hours", positive=True)
            for field in COUNTS:
                post[field] = number(raw.get(field), field, integer=True)
            if not missing(raw.get("saved")):
                saved = number(raw["saved"], "saved", integer=True)
                if post["saves"] is not None and post["saves"] != saved:
                    raise ValueError("saves and saved conflict")
                post["saves"] = saved
            post["interactions_derived"] = False
            components = [post[f] for f in ("likes", "comments", "saves", "shares")]
            if post["total_interactions"] is None and all(v is not None for v in components):
                post["total_interactions"] = sum(components)
                post["interactions_derived"] = True
            for rate, count in RATES.items():
                post[rate] = (post[count] / post["reach"]
                              if post["reach"] and post[count] is not None else None)
            for field in ("url", "caption"):
                if not missing(raw.get(field)):
                    if not isinstance(raw[field], str):
                        raise ValueError(f"{field} must be text")
                    post[field] = raw[field]
            posts.append(post)
        except ValueError as error:
            # Do not echo arbitrary source content in validation errors.
            raise ValueError(f"row {position}: {error}") from None
    return posts


def load_posts(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        if path.suffix.lower() == ".json":
            return normalize(json.load(handle))
        if path.suffix.lower() != ".csv":
            raise ValueError("input extension must be .csv or .json")
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV must have a header with unique column names")
        rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError("CSV row width must match the header")
        return normalize(rows)


def analyze(posts, threshold=3.0, baseline_method="mean", min_comparators=5):
    if not math.isfinite(threshold) or threshold <= 1:
        raise ValueError("threshold must be finite and greater than 1")
    if baseline_method not in {"mean", "median"}:
        raise ValueError("baseline must be mean or median")
    if isinstance(min_comparators, bool) or not isinstance(min_comparators, int) or min_comparators < 2:
        raise ValueError("min-comparators must be an integer of at least 2")
    reducer = statistics.mean if baseline_method == "mean" else statistics.median
    groups, excluded, results = defaultdict(list), [], []
    for post in posts:
        if post["paid"] is True:
            excluded.append({"post_id": post["post_id"], "account": post["account"],
                             "reason": "known paid/boosted distribution"})
        else:
            groups[(post["account"], post["format"], post["observation_window_hours"])].append(post)
    for group in groups.values():
        for post in group:
            comparisons, warnings = {}, []
            if post["paid"] is None:
                warnings.append("candidate paid status unknown")
            if post["observation_window_hours"] is None:
                warnings.append("observation window unknown; comparisons are exploratory")
            other = [p for p in group if p is not post]
            for metric in (*COUNTS, *RATES):
                value = post[metric]
                peers = [p for p in other if p[metric] is not None]
                values = [p[metric] for p in peers]
                baseline = float(reducer(values)) if values else None
                multiple = value / baseline if value is not None and baseline else None
                adequate = len(peers) >= min_comparators
                comparable = (adequate and post["observation_window_hours"] is not None
                              and post["paid"] is False and all(p["paid"] is False for p in peers))
                reasons = []
                if value is None:
                    reasons.append("post metric unavailable")
                if not values:
                    reasons.append("no measured comparators")
                elif not adequate:
                    reasons.append("thin comparator sample")
                if baseline == 0:
                    reasons.append("zero baseline; no multiple")
                if post["observation_window_hours"] is None:
                    reasons.append("unknown observation window")
                if post["paid"] is None or any(p["paid"] is None for p in peers):
                    reasons.append("unknown paid status in comparison")
                crosses = multiple is not None and multiple >= threshold
                comparisons[metric] = {
                    "value": value, "baseline": baseline, "multiple": multiple,
                    "comparators": len(peers), "crosses_threshold": crosses,
                    "adequate_comparable_data": comparable, "limitations": reasons,
                }
            crossed = [(m, c) for m, c in comparisons.items() if c["crosses_threshold"]]
            supported = [(m, c) for m, c in crossed if c["adequate_comparable_data"]]
            measurable = [(m, c) for m, c in comparisons.items() if c["multiple"] is not None]
            driving = max(supported or crossed or measurable,
                          key=lambda pair: pair[1]["multiple"], default=None)
            if not other:
                warnings.append("no other posts in this account/format/window")
            elif len(other) < min_comparators:
                warnings.append("thin comparator sample; flags are provisional")
            if any("unknown paid status in comparison" in c["limitations"] for c in comparisons.values()):
                warnings.append("one or more metric comparisons include unknown paid status")
            results.append({
                "post_id": post["post_id"], "account": post["account"],
                "format": post["format"], "url": post.get("url"),
                "observation_window_hours": post["observation_window_hours"],
                "interactions_derived": post["interactions_derived"],
                "outlier_flag": bool(supported),
                "provisional_flag": bool(crossed) and not supported,
                "driving_metric": driving[0] if driving else None,
                "driving_comparison": driving[1] if driving else None,
                "comparisons": comparisons, "warnings": warnings,
            })
    return {
        "schema_version": 1,
        "settings": {"threshold": threshold, "baseline": baseline_method,
                     "min_comparators": min_comparators, "leave_one_out": True},
        "meaning": "Organic screening only; flags are not paid-ad recommendations or statistical significance.",
        "publication_window": "selected by the user in the input; not inferred",
        "input_count": len(posts), "analyzed_count": len(results),
        "excluded": excluded, "posts": results,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="CSV or JSON file")
    parser.add_argument("--threshold", type=float, default=3.0)
    parser.add_argument("--baseline", choices=["mean", "median"], default="mean")
    parser.add_argument("--min-comparators", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        result = analyze(load_posts(args.input), args.threshold, args.baseline, args.min_comparators)
    except (OSError, UnicodeError, ValueError, csv.Error) as error:
        print(f"Cannot analyze: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
