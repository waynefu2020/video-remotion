"""Cover images for the schedule video -> dist/cover-9x16.png (1080x1920) and dist/cover-3x4.png (1080x1440)."""

import os
import random

from PIL import Image

import schedule_render as S
from render import asset, put, rich, txt, with_shadow
from timeline import INK, ORANGE, ORANGE_SOFT

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
W = 1080
CELL, GAP, GSIZE = 150, 12, 100
FILLERS = [("嗯，", -14, 150, 205), ("那个", 9, 905, 190), ("啊不是", -7, 120, 640), ("然后", 12, 930, 655)]


def cell_x(k, n=6):
    return W / 2 - (n * CELL + (n - 1) * GAP) / 2 + k * (CELL + GAP) + CELL / 2


def messy_row(img, y):
    rnd = random.Random(4)
    for k, s in enumerate("说话乱七八糟"):
        cell = Image.new("RGBA", (CELL + 8, CELL + 8), (0, 0, 0, 0))
        cell.alpha_composite(S.cell_img(CELL, S.ROSE_SOFT, S.ROSE_LINE, 3), (4, 4))
        g = S.glyph(s, GSIZE, S.ROSE)
        cell.alpha_composite(g, ((cell.width - g.width) // 2, (cell.height - g.height) // 2))
        put(img, cell, cell_x(k) + rnd.uniform(-10, 10), y + rnd.uniform(-22, 22), 1.0, 1.0,
            rotate=rnd.uniform(-11, 11))


def neat_row(img, y):
    for k, s in enumerate("日程井井有条"):
        hot = k >= 2
        fill, line = (ORANGE_SOFT, ORANGE) if hot else (S.CELL_FILL, S.CELL_LINE)
        put(img, S.cell_img(CELL, fill, line, 4 if hot else 3), cell_x(k), y)
        put(img, S.glyph(s, GSIZE, ORANGE if hot else INK), cell_x(k), y)


def fillers(img, dy):
    for text, rot, x, y in FILLERS:
        chip = S.chip(text, S.WHITE, S.ROSE, 34)
        chip = with_shadow(chip, blur=10, dy=6, opacity=0.15)[0]
        put(img, chip, x, y + dy, 1.0, 0.92, rotate=rot)


def calendar_crop():
    layer = Image.new("RGBA", (W, 1920), (0, 0, 0, 0))
    S.draw_calendar(layer, S.CAL_OUT - 0.2)
    return layer.crop((S.GX0 - 8, S.ROW_Y[0] - 8, S.GX0 + 7 * S.CAL_PITCH, 1130))


def brand_row(img, y):
    logo = asset("logo", height=84)
    name = txt("闪念贝壳", 46, "Black")
    slogan = rich((("帮你记，", INK), ("帮你做", ORANGE)), 40, "Black")
    gap = 22
    total = logo.width + gap + name.width + 36 + slogan.width
    x = W / 2 - total / 2
    put(img, logo, x, y, ax=0)
    x += logo.width + gap
    put(img, name, x, y, ax=0)
    x += name.width + 18
    put(img, S.rrect(4, 40, 2, S.CELL_LINE + (255,)), x, y)
    put(img, slogan, x + 18, y, ax=0)


def compose(h, dy):
    img = Image.new("RGBA", (W, h), S.PAPER + (255,))
    S.draw_header(img, S.CAL + 1)
    fillers(img, dy)
    messy_row(img, 320 + dy)
    neat_row(img, 510 + dy)
    put(img, txt("随口一说，自动排进日程", 40, "Bold", S.MUTED), W / 2, 660 + dy)
    cal = calendar_crop()
    k = 0.74
    put(img, cal, W / 2, 1000 + dy, k)
    brand_row(img, 1345 + dy)
    return img.convert("RGB")


def main():
    os.makedirs(DIST, exist_ok=True)
    for name, h, dy in (("cover-9x16.png", 1920, 220), ("cover-3x4.png", 1440, -20)):
        path = os.path.join(DIST, name)
        compose(h, dy).save(path)
        print(path)


if __name__ == "__main__":
    main()
