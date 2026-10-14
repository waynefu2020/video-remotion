#!/usr/bin/env python3
"""Mechanical preflight for a finished product-motion video."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def ratio(value: str) -> float:
    a, b = value.split("/")
    return float(a) / float(b)


def probe(path: Path) -> dict:
    result = run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ])
    return json.loads(result.stdout)


def integrated_loudness(path: Path) -> float | None:
    result = subprocess.run(
        ["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    matches = re.findall(r"\bI:\s*(-?\d+(?:\.\d+)?)\s+LUFS", result.stderr)
    return float(matches[-1]) if matches else None


def black_edge_score(image: Image.Image) -> dict[str, float]:
    rgb = image.convert("RGB")
    w, h = rgb.size
    bands = {
        "top": rgb.crop((0, 0, w, min(8, h))),
        "bottom": rgb.crop((0, max(0, h - 8), w, h)),
        "left": rgb.crop((0, 0, min(8, w), h)),
        "right": rgb.crop((max(0, w - 8), 0, w, h)),
    }
    scores = {}
    for name, band in bands.items():
        pixels = list(band.get_flattened_data())
        scores[name] = sum(max(p) < 12 for p in pixels) / max(1, len(pixels))
    return scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    args = parser.parse_args()
    path = Path(args.video).resolve()
    data = probe(path)

    video = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    duration = float(data["format"]["duration"])
    checks: list[tuple[bool, str]] = []

    checks.append((video is not None, "video stream exists"))
    if video:
        checks.extend([
            ((video.get("width"), video.get("height")) == (1080, 1920), "size is 1080×1920"),
            (abs(ratio(video.get("avg_frame_rate", "0/1")) - 30) < 0.05, "frame rate is 30 fps"),
            (video.get("pix_fmt") == "yuv420p", "pixel format is yuv420p"),
        ])
    checks.append((audio is not None, "audio stream exists"))
    checks.append((duration > 0, f"duration is {duration:.2f}s"))

    loudness = integrated_loudness(path) if audio else None
    checks.append((
        loudness is not None and -16.5 <= loudness <= -12.0,
        f"integrated loudness is {loudness:.1f} LUFS" if loudness is not None else "loudness could not be measured",
    ))

    worst = {"top": 0.0, "bottom": 0.0, "left": 0.0, "right": 0.0}
    with tempfile.TemporaryDirectory() as tmp:
        for index, at in enumerate((duration * 0.1, duration * 0.5, duration * 0.9)):
            still = Path(tmp) / f"{index}.png"
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", str(path), "-frames:v", "1", str(still)],
                check=True,
            )
            scores = black_edge_score(Image.open(still))
            for edge, score in scores.items():
                worst[edge] = max(worst[edge], score)
    checks.append((
        all(score < 0.8 for score in worst.values()),
        "no solid black edge band detected " + ", ".join(f"{k}={v:.0%}" for k, v in worst.items()),
    ))

    failed = False
    for passed, message in checks:
        print(("PASS" if passed else "FAIL") + "  " + message)
        failed |= not passed

    if failed:
        raise SystemExit(1)
    print("\nMechanical preflight passed. Continue with human visual review.")


if __name__ == "__main__":
    main()
