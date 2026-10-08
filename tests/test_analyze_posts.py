import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/organic-to-ads/scripts/analyze_posts.py"
spec = importlib.util.spec_from_file_location("analyze_posts", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def rows(values, **overrides):
    return [dict(post_id=f"p{i}", account="sample", format="carousel", paid=False,
                 observation_window_hours=48, saves=value, **overrides)
            for i, value in enumerate(values)]


class AnalyzerTests(unittest.TestCase):
    def calculate(self, raw, **kwargs):
        return module.analyze(module.normalize(raw), **kwargs)

    def test_leave_one_out_does_not_hide_candidate(self):
        result = self.calculate(rows([10, 10, 10, 10, 10, 60]))["posts"][-1]
        self.assertEqual(result["comparisons"]["saves"]["baseline"], 10)
        self.assertEqual(result["comparisons"]["saves"]["multiple"], 6)
        self.assertTrue(result["outlier_flag"])

    def test_paid_post_is_not_candidate_or_baseline(self):
        raw = rows([10, 10, 10, 10, 10, 60, 10000])
        raw[-1]["paid"] = True
        result = self.calculate(raw)
        self.assertEqual(len(result["excluded"]), 1)
        self.assertEqual(result["posts"][-1]["comparisons"]["saves"]["baseline"], 10)

    def test_formats_accounts_and_windows_are_not_pooled(self):
        raw = rows([10, 10, 10, 10, 10, 60])
        for field, value in [("format", "reel"), ("account", "other"),
                             ("observation_window_hours", 72)]:
            extra = dict(raw[0], post_id=f"different-{field}", saves=50000)
            extra[field] = value
            raw.append(extra)
        candidate = next(p for p in self.calculate(raw)["posts"] if p["post_id"] == "p5")
        self.assertEqual(candidate["comparisons"]["saves"]["comparators"], 5)
        self.assertEqual(candidate["comparisons"]["saves"]["baseline"], 10)

    def test_missing_parts_do_not_become_zero_interactions(self):
        raw = rows([10, 10], likes=10, comments=2)
        posts = module.normalize(raw)
        self.assertIsNone(posts[0]["total_interactions"])
        self.assertIsNone(posts[0]["engagement_rate"])

    def test_complete_components_derive_interactions_once(self):
        raw = rows([5], likes=10, comments=2, shares=3, reach=100)
        post = module.normalize(raw)[0]
        self.assertEqual(post["total_interactions"], 20)
        self.assertEqual(post["engagement_rate"], 0.2)
        raw[0]["total_interactions"] = 17
        self.assertEqual(module.normalize(raw)[0]["total_interactions"], 17)

    def test_zero_reach_and_baseline_never_create_infinity(self):
        candidate = self.calculate(rows([0, 0, 0, 0, 0, 60], reach=0))["posts"][-1]
        self.assertIsNone(candidate["comparisons"]["saves"]["multiple"])
        self.assertIsNone(candidate["comparisons"]["save_rate"]["value"])
        json.dumps(candidate, allow_nan=False)

    def test_thin_and_unknown_window_flags_are_provisional(self):
        for raw in [rows([10, 60]), rows([10, 10, 10, 10, 10, 60])]:
            if len(raw) > 2:
                for post in raw:
                    post.pop("observation_window_hours")
            candidate = self.calculate(raw)["posts"][-1]
            self.assertTrue(candidate["provisional_flag"])
            self.assertFalse(candidate["outlier_flag"])

    def test_unknown_paid_comparator_downgrades_affected_metric(self):
        raw = rows([10, 10, 10, 10, 10, 60])
        raw[0]["paid"] = None
        self.assertTrue(self.calculate(raw)["posts"][-1]["provisional_flag"])
        # A missing value never enters this metric's comparison set.
        raw[0]["saves"] = None
        candidate = self.calculate(raw, min_comparators=4)["posts"][-1]
        self.assertTrue(candidate["outlier_flag"])

    def test_median_and_threshold_options_change_screen(self):
        raw = rows([1, 1, 1, 1, 30, 10])
        mean = self.calculate(raw)["posts"][-1]
        median = self.calculate(raw, baseline_method="median")["posts"][-1]
        self.assertFalse(mean["outlier_flag"])
        self.assertTrue(median["outlier_flag"])
        self.assertFalse(self.calculate(raw, baseline_method="median", threshold=11)["posts"][-1]["outlier_flag"])

    def test_alias_and_invalid_input(self):
        raw = rows([10])
        raw[0].pop("saves")
        raw[0]["saved"] = 8
        self.assertEqual(module.normalize(raw)[0]["saves"], 8)
        for value in [-1, "NaN", "Infinity", 2.5, True, "1,000"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.normalize(rows([value]))
        raw[0]["saves"] = 9
        with self.assertRaises(ValueError):
            module.normalize(raw)
        for raw in [[], [None], rows([10]) * 2, [dict(rows([10])[0], paid="maybe")]]:
            with self.assertRaises(ValueError):
                module.normalize(raw)

    def test_cli_demo_and_malformed_csv(self):
        run = subprocess.run([sys.executable, str(SCRIPT), str(ROOT / "examples/posts.csv")],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        candidate = next(p for p in result["posts"] if p["post_id"] == "post-07")
        self.assertEqual(candidate["comparisons"]["saves"]["multiple"], 6)
        self.assertEqual(result["excluded"][0]["post_id"], "post-09")
        # Leave diagnostic fixtures in the system temp area; no cleanup deletion.
        scratch = Path(tempfile.mkdtemp(prefix="facebook-skill-input-"))
        bad = scratch / "bad.csv"
        bad.write_text("post_id,account,format\np1,a,carousel,extra\n")
        run = subprocess.run([sys.executable, str(SCRIPT), str(bad)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")

    def test_json_input_and_invalid_threshold(self):
        scratch = Path(tempfile.mkdtemp(prefix="facebook-skill-json-"))
        path = scratch / "posts.json"
        path.write_text(json.dumps(rows([10, 10, 10, 10, 10, 60])))
        self.assertEqual(len(module.load_posts(path)), 6)
        for threshold in [1, 0, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                module.analyze(module.load_posts(path), threshold=threshold)


if __name__ == "__main__":
    unittest.main()
