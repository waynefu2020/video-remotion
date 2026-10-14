"""English covers for the memory video -> dist/en/cover-en-9x16.png (1080x1920) and cover-en-3x4.png (1080x1440).

Key art stays inside the centre 1080x1440 band so the 9:16 cover survives the 3:4 profile-grid crop.
    VIDEO_LANG=en python3 memory_cover_en.py
"""

import os

os.environ.setdefault("VIDEO_LANG", "en")

from PIL import Image  # noqa: E402

import memory_render as M  # noqa: E402
from memory_timeline import FOUND_MARK  # noqa: E402
from render import asset, background, glow, label_chip, put, rich, txt  # noqa: E402
from timeline import GRAY, INK, ORANGE, ORANGE_SOFT  # noqa: E402

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "en")
W = 1080


def brand_row(img, y):
    logo = asset("logo", height=84)
    name = txt("ideaShell", 50, "Black")
    gap = 22
    total = logo.width + gap + name.width
    x = (W - total) / 2
    put(img, logo, x, y, ax=0)
    put(img, name, x + logo.width + gap, y, ax=0)


def cover(h):
    dy = (h - 1440) / 2
    top = (1920 - h) // 2
    img = background(0).convert("RGBA").crop((0, top, W, top + h))
    put(img, M.frozen_tunnel(), W / 2, h / 2, 1.0, 0.28)
    put(img, glow(1200, ORANGE, 0.4), W / 2, 760 + dy, 1.0, 0.8)
    put(img, label_chip("What was Mark's budget again?", ORANGE, ORANGE_SOFT, 36), W / 2, 250 + dy)
    put(img, txt("You forgot.", 132, "Black"), W / 2, 420 + dy)
    put(img, rich((("It ", INK), ("remembers", ORANGE), (".", INK)), 132, "Black"), W / 2, 570 + dy)
    put(img, M.found_card(FOUND_MARK + 1), W / 2, 880 + dy)
    put(img, txt("Your notes, calls and files — searchable by asking.", 36, "Medium", GRAY), W / 2, 1110 + dy)
    brand_row(img, 1250 + dy)
    return img.convert("RGB")


def main():
    os.makedirs(DIST, exist_ok=True)
    for name, h in (("cover-en-9x16.png", 1920), ("cover-en-3x4.png", 1440)):
        path = os.path.join(DIST, name)
        cover(h).save(path)
        print(path)


if __name__ == "__main__":
    main()
