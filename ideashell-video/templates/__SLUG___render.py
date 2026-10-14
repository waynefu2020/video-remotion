"""Render the「__TITLE__」video.

    python3 __SLUG___render.py                 # -> out/__SLUG__-video.mp4 (no audio)
    python3 __SLUG___render.py --stills 1 4 9  # PNG stills -> out/__SLUG__-still-*.png
"""

import argparse
import os
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

from PIL import Image

import render as R
from render import appear, asset, circle, prog, put, rich, rrect, text_width, txt, with_shadow, xhs_safe
from timeline import INK, ORANGE, WHITE
from __SLUG___timeline import *  # noqa: F403

OUT_DIR = R.OUT_DIR
PAPER = (246, 242, 236)
MUTED = (140, 126, 116)
CARD_W, CARD_H, CARD_Y0, CARD_STEP = 860, 180, 640, 230


def scene_hook(img, t):
    a = 1 - prog(t, HOOK_OUT, 0.3)
    n = sum(1 for t0 in hook_times() if t >= t0)
    if n == 0 or a <= 0:
        return
    x0 = W / 2 - text_width(HOOK, 76, "Black") / 2
    put(img, txt(HOOK[:n], 76, "Black"), x0, 900 - 60 * (1 - a), ax=0, alpha=a)


@lru_cache(8)
def point_card(k):
    head, body = POINTS[k]
    card = rrect(CARD_W, CARD_H, 36, WHITE + (255,)).copy()
    put(card, circle(104, ORANGE + (255,)), 110, CARD_H / 2)
    put(card, txt(head, 56, "Black", WHITE), 110, CARD_H / 2)
    put(card, txt(body, 48, "Bold"), 200, CARD_H / 2, ax=0)
    return with_shadow(card, blur=18, dy=10, opacity=0.1)[0]


def scene_points(img, t):
    out = prog(t, POINTS_OUT, 0.35)
    for k, t0 in enumerate(POINT_AT):
        a, s, dy = appear(t, t0)
        put(img, point_card(k), W / 2, CARD_Y0 + CARD_STEP * k + dy - 80 * out, s, a * (1 - out))


def scene_end(img, t):
    a, s, dy = appear(t, LOGO, 0.5, 30, 0.6)
    put(img, with_shadow(asset("logo", height=200), blur=16, dy=8, opacity=0.1)[0], W / 2, 760 + dy, s, a)
    a, s, dy = appear(t, TITLE_AT)
    put(img, txt("闪念贝壳", 96, "Black"), W / 2, 960 + dy, s, a)
    a, s, dy = appear(t, SLOGAN_AT)
    put(img, rich((("帮你记，", INK), ("帮你做", ORANGE)), 56, "Black"), W / 2, 1080 + dy, s, a)
    a, _, dy = appear(t, STORE_AT)
    put(img, txt("应用商店搜「闪念贝壳」", 34, "Bold", MUTED), W / 2, 1260 + dy, alpha=a)


def render(t):
    img = Image.new("RGBA", (W, H), PAPER + (255,))
    if t < HOOK_OUT + 0.4:
        scene_hook(img, t)
    if POINT_AT[0] - 0.1 <= t < POINTS_OUT + 0.4:
        scene_points(img, t)
    if t >= LOGO - 0.1:
        scene_end(img, t)
    return xhs_safe(img, PAPER)


def render_frame(i):
    return render(i / FPS).tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", nargs="*", type=float)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    if args.stills:
        for t in args.stills:
            path = os.path.join(OUT_DIR, f"__SLUG__-still-{t:05.2f}.png")
            render(t).save(path)
            print(path)
        return
    n = int(DURATION * FPS)
    out = os.path.join(OUT_DIR, "__SLUG__-video.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                           f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                           "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    with Pool(3) as pool:
        for i, frame in enumerate(pool.imap(render_frame, range(n), chunksize=4)):
            ff.stdin.write(frame)
            if i % 60 == 0:
                print(f"frame {i}/{n}", file=sys.stderr)
    ff.stdin.close()
    ff.wait()
    print(out)


if __name__ == "__main__":
    main()
