#!/usr/bin/env python3
"""Build a portable .skill archive containing this entire Skill."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(SKILL_DIR.parent / "dist" / "product-motion-video.skill"))
    args = parser.parse_args()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(SKILL_DIR.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, Path(SKILL_DIR.name) / path.relative_to(SKILL_DIR))

    print(output)


if __name__ == "__main__":
    main()
