import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/organic-to-ads/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("scan_instagram", SCRIPTS / "scan_instagram.py")
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)
NOW = dt.datetime(2026, 10, 8, 12, tzinfo=dt.timezone.utc)
# Short synthetic values, not live IDs or credentials.
FIXTURE_CREDENTIAL = "fixture-only-value"


def configuration():
    return dict(api_version="v26.0", instagram_user_id="101", account_label="demo",
                token_secret_name="META_ACCESS_TOKEN", lookback_days=90, min_age_hours=48,
                max_posts=200, max_pages=20, exclude_post_ids=[], outlier_threshold=3,
                baseline="mean", min_comparators=5)


def media(identifier, days=5, **overrides):
    return dict(id=str(identifier), timestamp=(NOW - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S%z"),
                media_type="IMAGE", media_product_type="FEED", caption="Actual source caption",
                permalink="https://www.instagram.com/p/fictional/", like_count=20, comments_count=3,
                media_url="https://example.com/fictional-image.jpg", **overrides)


def insights(saved=10):
    return {"data": [{"name": metric, "values": [{"value": value}]} for metric, value in
                     [("reach", 100), ("views", 150), ("saved", saved), ("shares", 5), ("total_interactions", saved + 28)]]}


class FakeClient:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, path, params=None):
        self.calls.append((path, dict(params or {})))
        route = self.routes[path]
        if callable(route):
            return route(params or {})
        if isinstance(route, Exception):
            raise route
        return route


class Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.payload[:size]


class FakeOpener:
    def __init__(self, responses):
        self.responses, self.requests = iter(responses), []

    def open(self, request, timeout):
        self.requests.append(request)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return Response(response)


class CollectorTests(unittest.TestCase):
    def test_meta_compact_and_iso_offsets_select_the_same_post(self):
        stamps = ["2026-10-03T12:00:00+0000", "2026-10-03T12:00:00+00:00",
                  "2026-10-03T12:00:00Z", "2026-10-03T05:00:00-0700"]
        for stamp in stamps:
            with self.subTest(timestamp=stamp):
                raw = media(201)
                raw["timestamp"] = stamp
                client = FakeClient({"101": {"username": "fictional"},
                                     "101/media": {"data": [raw]}, "201/insights": insights()})
                result = scan.collect(client, configuration(), NOW)
                self.assertEqual([p["post_id"] for p in result["posts"]], ["201"])
                self.assertEqual(result["posts"][0]["measurement_age_hours"], 120)
                self.assertEqual(result["posts"][0]["posted_at"], "2026-10-03T12:00:00+00:00")

    def test_unreadable_timestamps_cannot_be_an_empty_success(self):
        raw = media(201)
        raw["timestamp"] = "not-a-timestamp"
        client = FakeClient({"101": {"username": "fictional"}, "101/media": {"data": [raw]}})
        with self.assertRaises(scan.ScanError):
            scan.collect(client, configuration(), NOW)
        good = media(202)
        client = FakeClient({"101": {"username": "fictional"},
                             "101/media": {"data": [raw, good]}, "202/insights": insights()})
        result = scan.collect(client, configuration(), NOW)
        self.assertEqual([p["post_id"] for p in result["posts"]], ["202"])
        self.assertTrue(any("publication timestamps" in w for w in result["warnings"]))

    def test_complete_scan_captions_metrics_and_directional_outlier(self):
        raw = [media(i) for i in range(201, 207)]
        for item in raw:
            item["media_type"] = "CAROUSEL_ALBUM"
        routes = {"101": {"id": "101", "username": "fictional-demo", "followers_count": 500},
                  "101/media": {"data": raw},
                  "206/children": {"data": [{"id": "301", "media_type": "IMAGE", "media_url": "https://example.com/slide.jpg"}]}}
        routes.update({f"{i}/insights": insights(saved=60 if i == 206 else 10) for i in range(201, 207)})
        routes.update({f"{i}/children": {"data": []} for i in range(201, 206)})
        result = scan.collect(FakeClient(routes), configuration(), NOW)
        self.assertEqual(len(result["posts"]), 6)
        self.assertEqual(result["posts"][-1]["children"][0]["id"], "301")
        self.assertEqual(result["posts"][0]["caption"], "Actual source caption")
        winner = result["analysis"]["posts"][-1]
        self.assertEqual(winner["comparisons"]["saves"]["multiple"], 6)
        self.assertTrue(winner["provisional_flag"])
        self.assertFalse(winner["outlier_flag"])
        self.assertFalse(result["coverage"]["truncated"])
        self.assertEqual(result["posts"][0]["measurement_age_hours"], 120)

    def test_recent_old_paid_story_and_user_exclusions(self):
        raw = [media(201, days=1), media(202, days=100), media(203), media(204), media(205), media(206)]
        raw[2]["media_product_type"] = "AD"
        raw[3]["media_product_type"] = "STORY"
        config = configuration()
        config["exclude_post_ids"] = ["205"]
        client = FakeClient({"101": {"username": "fictional"}, "101/media": {"data": raw}, "206/insights": insights()})
        result = scan.collect(client, config, NOW)
        self.assertEqual([p["post_id"] for p in result["posts"]], ["206"])
        self.assertEqual(len(result["coverage"]["exclusions"]), 5)

    def test_metric_batch_isolation_and_missing_is_not_zero(self):
        def route(params):
            if "," in params["metric"] or params["metric"] == "views":
                raise scan.GraphError(code=100, unsupported_metric=True)
            return {"data": [{"name": params["metric"], "total_value": {"value": 0}}]}
        client = FakeClient({"201/insights": route})
        values, missing = scan.media_insights(client, "201")
        self.assertNotIn("views", values)
        self.assertEqual(values["saved"], 0)
        self.assertEqual(missing, ["views"])
        self.assertEqual(len(client.calls), 6)
        for code in (190, 10, 200, 4):
            client = FakeClient({"201/insights": scan.GraphError(code=code)})
            with self.assertRaises(scan.GraphError):
                scan.media_insights(client, "201")
            self.assertEqual(len(client.calls), 1)

    def test_generic_code_100_fails_instead_of_missing_insights(self):
        for subcode in (None, 33):
            failure = scan.GraphError(code=100, subcode=subcode, error_type="GraphMethodException")
            client = FakeClient({"101": {"username": "fictional"},
                                 "101/media": {"data": [media(201)]}, "201/insights": failure})
            with self.assertRaises(scan.GraphError):
                scan.collect(client, configuration(), NOW)
            self.assertEqual(len([c for c in client.calls if c[0].endswith("/insights")]), 1)

    def test_isolated_metric_access_failure_is_not_suppressed(self):
        def route(params):
            if "," in params["metric"]:
                raise scan.GraphError(code=100, unsupported_metric=True)
            raise scan.GraphError(code=100, subcode=33)
        client = FakeClient({"201/insights": route})
        with self.assertRaises(scan.GraphError):
            scan.media_insights(client, "201")
        self.assertEqual(len(client.calls), 2)

    def test_pagination_uses_cursors_not_untrusted_next_urls(self):
        def route(params):
            return ({"data": [{"id": "202"}]} if params.get("after") == "cursor-b" else
                    {"data": [{"id": "201"}], "paging": {"next": "https://untrusted.example/", "cursors": {"after": "cursor-b"}}})
        client = FakeClient({"101/media": route})
        result = list(scan.pages(client, "101/media", {"limit": 50}, 2))
        self.assertEqual(result[-1][0][0]["id"], "202")
        self.assertEqual(client.calls[-1][1]["after"], "cursor-b")
        self.assertFalse(result[-1][1])
        capped = list(scan.pages(FakeClient({"101/media": route}), "101/media", {}, 1))
        self.assertTrue(capped[0][1])

    def test_malformed_and_repeated_pagination_is_not_empty_success(self):
        for response in [{"data": None}, {"data": [], "paging": {"next": "yes"}},
                         {"data": [], "paging": {"next": "yes", "cursors": {"after": "same"}}}]:
            with self.assertRaises(scan.ScanError):
                list(scan.pages(FakeClient({"101/media": response}), "101/media", {}, 3))

    def test_malformed_baseline_returns_friendly_cli_error_before_credentials(self):
        scratch = Path(tempfile.mkdtemp(prefix="organic-baseline-"))
        for value in ([], {}, None, 1, True, "invalid"):
            with self.subTest(value=value):
                config = configuration()
                config["baseline"] = value
                path = scratch / "config.json"
                path.write_text(json.dumps(config))
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch.object(scan, "load_token") as token, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    result = scan.main(["check", "--config", str(path)])
                self.assertEqual(result, 2)
                token.assert_not_called()
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("baseline must be mean or median", stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_caps_are_explicit_and_empty_window_is_real(self):
        config = configuration()
        config["max_posts"] = 1
        routes = {"101": {"username": "fictional"}, "101/media": {"data": [media(201), media(202)]}, "201/insights": insights()}
        result = scan.collect(FakeClient(routes), config, NOW)
        self.assertTrue(result["coverage"]["truncated"])
        routes["101/media"] = {"data": [media(201, days=1)]}
        result = scan.collect(FakeClient(routes), config, NOW)
        self.assertEqual(result["analysis"]["posts"], [])
        self.assertEqual(result["coverage"]["eligible_posts"], 0)

    def test_connection_check_requires_actual_reach(self):
        routes = {"101": {"username": "fictional"}, "101/media": {"data": [{"id": "201"}]}, "201/insights": insights()}
        self.assertTrue(scan.check_access(FakeClient(routes), configuration())["insights_verified"])
        routes["201/insights"] = {"data": []}
        self.assertFalse(scan.check_access(FakeClient(routes), configuration())["insights_verified"])
        routes["201/insights"] = scan.GraphError(code=190)
        with self.assertRaises(scan.GraphError):
            scan.check_access(FakeClient(routes), configuration())

    def test_output_is_private_and_not_in_public_repository(self):
        scratch = Path(tempfile.mkdtemp(prefix="facebook-meta-output-"))
        bundle = {"posts": [], "analysis": {"posts": []}}
        output = scan.write_bundle(bundle, scratch / "new-run")
        self.assertEqual(json.loads((output / "posts.json").read_text()), [])
        if os.name != "nt":
            self.assertEqual((output / "scan.json").stat().st_mode & 0o777, 0o600)
        with self.assertRaises(scan.ScanError):
            scan.write_bundle(bundle, output)
        with self.assertRaises(scan.ScanError):
            scan.write_bundle(bundle, ROOT / "private-scan")
        with self.assertRaises(scan.ScanError):
            scan.write_bundle(bundle, SCRIPTS / "private-scan")

    def test_config_rejects_credentials_and_requires_real_settings(self):
        scratch = Path(tempfile.mkdtemp(prefix="facebook-meta-config-"))
        path = scratch / "config.json"
        for overrides in [{"api_version": ""}, {"instagram_user_id": "act_placeholder"},
                          {"token": "do-not-store"}, {"max_posts": 0},
                          {"min_age_hours": 3000}, {"outlier_threshold": float("nan")}]:
            path.write_text(json.dumps(dict(configuration(), **overrides)))
            with self.assertRaises(scan.ScanError):
                scan.read_config(path)
        path.write_text(json.dumps(configuration()))
        self.assertEqual(scan.read_config(path)["instagram_user_id"], "101")

    def test_scan_command_saves_content_and_analysis_without_credentials(self):
        scratch = Path(tempfile.mkdtemp(prefix="facebook-meta-command-"))
        config_path = scratch / "config.json"
        config_path.write_text(json.dumps(configuration()))
        output = scratch / "run"
        client = FakeClient({"101": {"username": "fictional"}, "101/media": {"data": [media(201)]}, "201/insights": insights()})
        client.token = FIXTURE_CREDENTIAL
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(scan, "load_token", return_value=FIXTURE_CREDENTIAL), patch.object(scan, "GraphClient", return_value=client), patch.object(scan.dt, "datetime", wraps=dt.datetime) as clock, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            clock.now.return_value = NOW
            result = scan.main(["scan", "--config", str(config_path), "--output-dir", str(output)])
        self.assertEqual(result, 0, stderr.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())["posts_scanned"], 1)
        self.assertEqual(json.loads((output / "posts.json").read_text())[0]["caption"], "Actual source caption")
        for path in output.iterdir():
            self.assertNotIn(FIXTURE_CREDENTIAL, path.read_text())


class TransportTests(unittest.TestCase):
    def test_get_only_authorization_header_no_token_url(self):
        opener = FakeOpener([{"username": "fictional"}])
        client = scan.GraphClient("v26.0", FIXTURE_CREDENTIAL, opener=opener)
        client.get("101", {"fields": "username"})
        request = opener.requests[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Authorization"), "Bearer " + FIXTURE_CREDENTIAL)
        self.assertNotIn(FIXTURE_CREDENTIAL, request.full_url)
        for path in ["https://other.example/", "101/ads", "101?bad=yes"]:
            with self.assertRaises(scan.ScanError):
                client.get(path)
        with self.assertRaises(scan.ScanError):
            client.get("101", {"access_token": FIXTURE_CREDENTIAL})
        with self.assertRaises(scan.ScanError):
            client.get("101/media", {"after": FIXTURE_CREDENTIAL})

    def test_sanitized_errors_and_bounded_retry(self):
        raw = {"error": {"code": 190, "message": "upstream echoed " + FIXTURE_CREDENTIAL}}
        opener = FakeOpener([raw])
        client = scan.GraphClient("v26.0", FIXTURE_CREDENTIAL, opener=opener)
        with self.assertRaises(scan.GraphError) as error:
            client.get("101")
        self.assertNotIn(FIXTURE_CREDENTIAL, str(error.exception))
        self.assertEqual(len(opener.requests), 1)
        transient = {"error": {"code": 4, "message": FIXTURE_CREDENTIAL}}
        waits = []
        opener = FakeOpener([transient] * 3)
        with self.assertRaises(scan.GraphError):
            scan.GraphClient("v26.0", FIXTURE_CREDENTIAL, opener=opener, sleep=waits.append).get("101")
        self.assertEqual(len(opener.requests), 3)
        self.assertEqual(waits, [1, 2])

    def test_metric_error_classification_keeps_only_safe_metadata(self):
        cases = [
            ({"code": 100, "type": "OAuthException", "message": "metric must be one of reach, saved " + FIXTURE_CREDENTIAL}, True),
            ({"code": 100, "message": "The value must be a valid insights metric"}, True),
            ({"code": 100, "message": "Metric views is not supported for this media"}, True),
            ({"code": 100, "error_subcode": 33, "type": "GraphMethodException", "message": FIXTURE_CREDENTIAL}, False),
            ({"code": 100, "message": "Unsupported get request " + FIXTURE_CREDENTIAL}, False),
            ({"code": 100, "message": "Unknown field on this object"}, False),
            ({"code": 100, "type": {}, "message": "metric must be one of reach"}, False),
            ({"code": 100, "error_subcode": 33, "message": "metric must be one of reach"}, False),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                opener = FakeOpener([{"error": raw}])
                with self.assertRaises(scan.GraphError) as caught:
                    scan.GraphClient("v26.0", FIXTURE_CREDENTIAL, opener=opener).get("201/insights", {"metric": "views"})
                error = caught.exception
                self.assertEqual(error.unsupported_metric, expected)
                self.assertEqual(error.subcode, raw.get("error_subcode"))
                self.assertNotIn(FIXTURE_CREDENTIAL, str(error))
                self.assertNotIn(FIXTURE_CREDENTIAL, repr(vars(error)))
                self.assertFalse(hasattr(error, "message"))

    def test_redirects_are_rejected(self):
        with self.assertRaises(scan.ScanError):
            scan.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.example")

    def test_keychain_resolution_does_not_fall_back_after_failure(self):
        success = subprocess.CompletedProcess([], 0, stdout=FIXTURE_CREDENTIAL + "\n", stderr="")
        with patch.object(scan.shutil, "which", return_value="/fixture/get_secret"), patch.object(scan.subprocess, "run", return_value=success) as called:
            self.assertEqual(scan.load_token("META_ACCESS_TOKEN"), FIXTURE_CREDENTIAL)
            self.assertEqual(called.call_args.args[0], ["/fixture/get_secret", "META_ACCESS_TOKEN"])
        failure = subprocess.CompletedProcess([], 1, stdout="", stderr=FIXTURE_CREDENTIAL)
        with patch.object(scan.shutil, "which", return_value="/fixture/get_secret"), patch.object(scan.subprocess, "run", return_value=failure):
            with self.assertRaises(scan.ScanError) as error:
                scan.load_token("META_ACCESS_TOKEN")
            self.assertNotIn(FIXTURE_CREDENTIAL, str(error.exception))
        with patch.object(scan.shutil, "which", return_value=None), patch.object(scan.sys, "platform", "darwin"):
            with self.assertRaises(scan.ScanError):
                scan.load_token("META_ACCESS_TOKEN")

    def test_discovery_only_returns_assigned_linked_accounts(self):
        client = FakeClient({"me/accounts": {"data": [{"id": "401", "name": "Demo page", "instagram_business_account": {"id": "101", "username": "fictional"}}, {"id": "402", "name": "Unlinked"}]}})
        result = scan.discover(client)
        self.assertEqual(len(result["accounts"]), 1)
        self.assertEqual(result["accounts"][0]["instagram_user_id"], "101")

    def test_cli_never_prints_token_echoed_in_discovery(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(scan, "load_token", return_value=FIXTURE_CREDENTIAL), patch.object(scan, "discover", return_value={"echo": FIXTURE_CREDENTIAL}), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = scan.main(["discover", "--api-version", "v26.0"])
        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn(FIXTURE_CREDENTIAL, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
