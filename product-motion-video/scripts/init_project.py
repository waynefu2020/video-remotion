#!/usr/bin/env python3
"""Create a complete, runnable product-motion-video project from this Skill."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
STARTER = SKILL_DIR / "starter"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="New project directory")
    parser.add_argument("--slug", required=True, help="Lowercase module name, e.g. meeting_notes")
    parser.add_argument("--title", required=True, help="Human-readable video theme")
    parser.add_argument("--force", action="store_true", help="Allow an existing empty output directory")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z][a-z0-9_]*", args.slug):
        sys.exit("slug must start with a letter and contain only lowercase letters, digits and underscores")

    output = Path(args.output).expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        sys.exit(f"output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    if not STARTER.is_dir():
        sys.exit(f"starter is missing: {STARTER}")

    for item in STARTER.iterdir():
        target = output / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)

    subprocess.run(
        [sys.executable, "new_video.py", args.slug, args.title],
        cwd=output,
        check=True,
    )

    build = output / f"build_{args.slug}.sh"
    build.chmod(build.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    (output / "requirements.txt").write_text("Pillow>=12.0.0\nnumpy>=1.26.0\n", encoding="utf-8")
    (output / ".gitignore").write_text("fonts/\nout/\n__pycache__/\n*.pyc\n.env*\n", encoding="utf-8")
    (output / "PROJECT.md").write_text(
        f"# {args.title}\n\n"
        f"- slug: `{args.slug}`\n"
        "- format: 1080×1920, 30 fps, no voice by default\n"
        f"- build: `./build_{args.slug}.sh`\n"
        f"- output: `dist/ideashell-{args.slug}.mp4`\n\n"
        "Replace the starter storyboard with the approved storyboard before delivery.\n",
        encoding="utf-8",
    )

    print(f"\nCreated: {output}")
    print(f"Next: cd {output} && ./build_{args.slug}.sh")


if __name__ == "__main__":
    main()
