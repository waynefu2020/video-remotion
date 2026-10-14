#!/usr/bin/env python3
"""Create a contact sheet from a video for fast visual review."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path


def duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--output")
    parser.add_argument("--fps", type=float, default=2.0, help="Frames sampled per second")
    args = parser.parse_args()

    video = Path(args.video).resolve()
    output = Path(args.output).resolve() if args.output else video.with_name(video.stem + "-sheet.png")
    frames = max(1, math.ceil(duration(video) * args.fps))
    cols = 6
    rows = math.ceil(frames / cols)

    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(video),
            "-vf", f"fps={args.fps},scale=180:-1,tile={cols}x{rows}:padding=4:margin=4:color=white",
            "-frames:v", "1", str(output),
        ],
        check=True,
    )
    print(output)


if __name__ == "__main__":
    main()
