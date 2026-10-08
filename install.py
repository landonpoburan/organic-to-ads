#!/usr/bin/env python3
"""Copy the skill into an explicitly chosen local skills directory."""

import argparse
import shutil
import sys
from pathlib import Path

NAME = "organic-to-ads"
# Copy only release resources, never exports, credentials, caches, or user reports.
FILES = (
    "SKILL.md", "LICENSE", "agents/openai.yaml", "references/analysis.md",
    "references/expansion.md", "references/data-input.md", "scripts/analyze_posts.py",
    "references/instagram-setup.md", "references/meta-config.example.json", "scripts/scan_instagram.py",
    "references/report-format.md", "references/weekly-review.md",
    "references/creative-review.md",
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("codex", "claude"), required=True)
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument("--project", type=Path, help="existing project directory")
    location.add_argument("--skills-dir", type=Path, help="explicit skills parent directory")
    parser.add_argument("--dry-run", action="store_true", help="show the destination without writing")
    args = parser.parse_args(argv)
    source = Path(__file__).resolve().parent / "skills" / NAME
    for relative in FILES:
        file = source / relative
        if not file.is_file() or file.is_symlink() or any(p.is_symlink() for p in file.parents if p != source.parent):
            print(f"Refusing invalid source resource: {relative}", file=sys.stderr)
            return 2
    if args.project:
        project = args.project.expanduser().resolve()
        if not project.is_dir():
            print("Project directory must already exist.", file=sys.stderr)
            return 2
        parent = project / (".agents" if args.target == "codex" else ".claude") / "skills"
    else:
        parent = args.skills_dir.expanduser().resolve()
    destination = parent / NAME
    if destination.exists() or destination.is_symlink():
        print(f"Refusing to overwrite existing destination: {destination}", file=sys.stderr)
        return 2
    print(f"{'Would install' if args.dry_run else 'Installing'} {NAME} for {args.target} at {destination}")
    if args.dry_run:
        return 0
    try:
        destination.mkdir(parents=True, exist_ok=False)
        for relative in FILES:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
    except OSError:
        print("Installation failed. The displayed destination may contain a partial copy; inspect it before retrying.", file=sys.stderr)
        return 2
    print("Installed. Start a fresh assistant session in that project and invoke the skill.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
