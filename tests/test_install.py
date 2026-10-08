import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def run_install(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "install.py"), *args],
                              capture_output=True, text=True)

    def test_project_install_and_overwrite_refusal(self):
        for host, folder in [("codex", ".agents"), ("claude", ".claude")]:
            project = Path(tempfile.mkdtemp(prefix="facebook skill project "))
            args = ["--target", host, "--project", str(project)]
            destination = project / folder / "skills/organic-to-ads"
            dry = self.run_install(*args, "--dry-run")
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertFalse(destination.exists())
            installed = self.run_install(*args)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            self.assertEqual(len([p for p in destination.rglob("*") if p.is_file()]), 13)
            scan = subprocess.run([sys.executable, str(destination / "scripts/scan_instagram.py"), "--help"],
                                  capture_output=True, text=True)
            self.assertEqual(scan.returncode, 0, scan.stderr)
            self.assertEqual((destination / "SKILL.md").read_bytes(),
                             (ROOT / "skills/organic-to-ads/SKILL.md").read_bytes())
            self.assertEqual((destination / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
            refused = self.run_install(*args)
            self.assertEqual(refused.returncode, 2)
            self.assertIn("Refusing to overwrite", refused.stderr)

    def test_custom_location_and_missing_project(self):
        scratch = Path(tempfile.mkdtemp(prefix="facebook-skill-custom-"))
        custom = scratch / "custom skills"
        installed = self.run_install("--target", "codex", "--skills-dir", str(custom))
        self.assertEqual(installed.returncode, 0, installed.stderr)
        self.assertTrue((custom / "organic-to-ads/SKILL.md").is_file())
        rejected = self.run_install("--target", "claude", "--project", str(scratch / "missing"))
        self.assertEqual(rejected.returncode, 2)
        self.assertFalse((scratch / "missing").exists())

    def test_dangling_destination_symlink_is_not_overwritten(self):
        scratch = Path(tempfile.mkdtemp(prefix="facebook-skill-symlink-"))
        (scratch / "organic-to-ads").symlink_to(scratch / "missing", target_is_directory=True)
        rejected = self.run_install("--target", "codex", "--skills-dir", str(scratch))
        self.assertEqual(rejected.returncode, 2)
        self.assertTrue((scratch / "organic-to-ads").is_symlink())


if __name__ == "__main__":
    unittest.main()
