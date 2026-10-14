"""Scaffold a new video from templates/ that renders end to end on the first run.

    python3 new_video.py todo_demo "随口一说，自动排好"
    ./build_todo_demo.sh

Creates todo_demo_timeline.py, todo_demo_render.py, todo_demo_audio.py and build_todo_demo.sh next to this file.
"""

import argparse
import os
import re
import stat
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(ROOT, "templates")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="lowercase module prefix, e.g. todo_demo")
    ap.add_argument("title", help="video theme, used in docstrings")
    args = ap.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", args.slug):
        sys.exit("slug must be lowercase letters, digits and underscores, starting with a letter")
    plan = [(name, os.path.join(ROOT, name.replace("__SLUG__", args.slug))) for name in sorted(os.listdir(TEMPLATES))]
    clash = [dst for _, dst in plan if os.path.exists(dst)]
    if clash:
        sys.exit("already exists: " + ", ".join(os.path.basename(p) for p in clash))
    for name, dst in plan:
        with open(os.path.join(TEMPLATES, name), encoding="utf-8") as f:
            body = f.read().replace("__SLUG__", args.slug).replace("__TITLE__", args.title)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(body)
        if dst.endswith(".sh"):
            os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(os.path.relpath(dst, ROOT))


if __name__ == "__main__":
    main()
