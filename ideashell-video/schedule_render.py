"""Render the 28s「说话乱七八糟，日程井井有条」video.

    python3 schedule_render.py                  # -> out/schedule-video.mp4 (no audio)
    python3 schedule_render.py --stills 3 17.5  # PNG stills -> out/s-still-*.png
"""

import argparse
import math
import os
import random
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

from PIL import Image, ImageDraw

import render as R
from render import (SS, appear, asset, check_badge, clamp, font, in_out, lerp, out_back, out_cubic, prog, put, rich,
                    ring, rrect, text_width, txt, with_shadow)
from timeline import INK, ORANGE, ORANGE_SOFT, WHITE
from schedule_timeline import *  # noqa: F403

OUT_DIR = R.OUT_DIR
PAPER = (246, 242, 236)
CELL_FILL = (255, 253, 250)
CELL_LINE = (232, 222, 212)
HEAD_LINE = (226, 219, 210)
MUTED = (140, 126, 116)
ROSE = (214, 51, 84)
ROSE_SOFT = (253, 229, 234)
ROSE_LINE = (240, 168, 184)
CHIP_GRAY = (240, 235, 228)

GX0, GY0, CELL, PITCH, COLS = 88, 330, 106, 114, 8
GLYPH = 62
CARD_W, CARD_H, CARD_Y0, CARD_STEP = 904, 150, 330, 172
TITLE_SIZE = 46


# ---------------------------------------------------------------- primitives

def cell_center(i):
    return GX0 + (i % COLS) * PITCH + CELL / 2, GY0 + (i // COLS) * PITCH + CELL / 2


def glyph_size(s, size, fit=True):
    return size if len(s) == 1 or not fit else int(size * 0.6)


@lru_cache(2048)
def glyph(s, size, color=INK, weight="Black", fit=True):
    f = font(weight, glyph_size(s, size, fit))
    w = int(max(size, f.getlength(s)) + 10)
    h = int(size * 1.3)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((w / 2, h / 2 - size * 0.05), s, font=f, fill=color, anchor="mm")
    return img


@lru_cache(64)
def cell_img(size, fill=CELL_FILL, line=CELL_LINE, width=2):
    return rrect(size, size, 3, fill + (255,), line + (255,), width)


def draw_rect(d, x, y, w, h, fill, line, width=2, r=3):
    d.rounded_rectangle((round(x), round(y), round(x + w) - 1, round(y + h) - 1), r, fill=fill, outline=line,
                        width=width)


def fade_img(img, a):
    return R.with_alpha(img, clamp(a))


@lru_cache(32)
def chip(label, color, fill, size=22):
    w = int(text_width(label, size)) + 26
    img = rrect(w, size + 18, 8, fill + (255,)).copy()
    put(img, txt(label, size, "Bold", color), w / 2, (size + 18) / 2)
    return img


@lru_cache(32)
def tag_icon(kind, size, color):
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(2, int(s * 0.11))
    c = color + (255,)
    if kind == "clock":
        d.ellipse((w / 2, w / 2, s - w / 2, s - w / 2), outline=c, width=w)
        d.line((s / 2, s * 0.26, s / 2, s * 0.52, s * 0.7, s * 0.62), fill=c, width=w, joint="curve")
    elif kind == "bell":
        d.chord((s * 0.18, s * 0.1, s * 0.82, s * 0.86), 180, 360, fill=c)
        d.rectangle((s * 0.18, s * 0.46, s * 0.82, s * 0.7), fill=c)
        d.rectangle((s * 0.1, s * 0.66, s * 0.9, s * 0.74), fill=c)
        d.ellipse((s * 0.4, s * 0.76, s * 0.6, s * 0.94), fill=c)
    elif kind == "repeat":
        d.arc((w, w, s - w, s - w), 205, 335, fill=c, width=w)
        d.arc((w, w, s - w, s - w), 25, 155, fill=c, width=w)
        a = s * 0.2
        d.polygon([(s * 0.86, s * 0.22), (s * 0.86, s * 0.22 + a), (s * 0.86 - a, s * 0.22 + a * 0.5)], fill=c)
        d.polygon([(s * 0.14, s * 0.78), (s * 0.14, s * 0.78 - a), (s * 0.14 + a, s * 0.78 - a * 0.5)], fill=c)
    elif kind == "list":
        for k in range(3):
            y = s * (0.22 + 0.28 * k)
            d.ellipse((s * 0.04, y - w * 0.8, s * 0.04 + w * 1.6, y + w * 0.8), fill=c)
            d.rounded_rectangle((s * 0.3, y - w / 2, s * 0.96, y + w / 2), w / 2, fill=c)
    elif kind == "cal":
        d.rounded_rectangle((w / 2, s * 0.16, s - w / 2, s - w / 2), s * 0.12, outline=c, width=w)
        d.rectangle((w / 2, s * 0.16, s - w / 2, s * 0.38), fill=c)
        for x in (0.3, 0.7):
            d.rounded_rectangle((s * x - w / 2, s * 0.04, s * x + w / 2, s * 0.26), w / 2, fill=c)
        for k in range(3):
            d.rectangle((s * (0.2 + 0.24 * k), s * 0.56, s * (0.32 + 0.24 * k), s * 0.68), fill=c)
    elif kind == "phone":
        d.rounded_rectangle((s * 0.28, s * 0.06, s * 0.72, s * 0.94), s * 0.12, outline=c, width=w)
    elif kind == "laptop":
        d.rounded_rectangle((s * 0.14, s * 0.2, s * 0.86, s * 0.68), s * 0.05, outline=c, width=w)
        d.rounded_rectangle((s * 0.02, s * 0.76, s * 0.98, s * 0.76 + w), w / 2, fill=c)
    elif kind == "watch":
        d.rounded_rectangle((s * 0.24, s * 0.24, s * 0.76, s * 0.76), s * 0.14, outline=c, width=w)
        d.rounded_rectangle((s * 0.36, s * 0.04, s * 0.64, s * 0.24), w / 2, fill=c)
        d.rounded_rectangle((s * 0.36, s * 0.76, s * 0.64, s * 0.96), w / 2, fill=c)
    return img.resize((size, size), Image.LANCZOS)


@lru_cache(32)
def tag_img(kind, text):
    color = ORANGE if kind == "clock" else MUTED
    fill = ORANGE_SOFT if kind == "clock" else CHIP_GRAY
    tw = int(text_width(text, 25, "Bold"))
    w = tw + 72
    img = rrect(w, 48, 12, fill + (255,)).copy()
    put(img, tag_icon(kind, 24, color), 30, 24)
    put(img, txt(text, 25, "Bold", color), 50, 24, ax=0)
    return img


# ---------------------------------------------------------------- chrome

def page_at(t):
    n = 1
    for t0, p in PAGES:
        if t >= t0:
            n = p
    return n


def draw_header(layer, t):
    put(layer, txt("闪念贝壳", 34, "Bold"), 62, 73, ax=0)
    page = page_at(t)
    prev = page - 1
    t_change = max([t0 for t0, p in PAGES if p == page])
    q = out_cubic(prog(t, t_change, 0.3)) if page > 1 else 1.0
    right = 1018
    num = f"0{page}/03"
    nw = text_width(num, 32, "Bold")
    put(layer, txt("语音待办 · ", 32, "Bold", MUTED), right - nw, 73, ax=1)
    put(layer, txt(num, 32, "Bold", MUTED), right, 73 + 24 * (1 - q), ax=1, alpha=q)
    if q < 1 and prev >= 1:
        put(layer, txt(f"0{prev}/03", 32, "Bold", MUTED), right, 73 - 24 * q, ax=1, alpha=1 - q)
    ImageDraw.Draw(layer).rectangle((60, 100, 1020, 101), fill=HEAD_LINE + (255,))


def label_icon(kind, t):
    if kind == "mic":
        img = Image.new("RGBA", (44, 44), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for k in range(4):
            h = 10 + 26 * (0.5 + 0.5 * math.sin(t * 11 + k * 1.7)) ** 1.2
            d.rounded_rectangle((4 + k * 10, 22 - h / 2, 10 + k * 10, 22 + h / 2), 3, fill=ORANGE + (255,))
        return img
    if kind == "logo":
        return asset("logo", height=48)
    if kind == "check":
        return check_badge(42)
    return tag_icon(kind, 40, ORANGE)


def draw_label(layer, t):
    cur = None
    for k, (t0, kind, text) in enumerate(LABELS):
        if t >= t0:
            cur = k
    if cur is None:
        return
    for k in (cur - 1, cur):
        if k < 0:
            continue
        t0, kind, text = LABELS[k]
        if not kind:
            continue
        if k == cur:
            a, s, dy = appear(t, t0 + 0.05, 0.32, rise=24, from_scale=0.92)
        else:
            o = prog(t, LABELS[cur][0], 0.16)
            a, s, dy = 1 - o, 1.0, -24 * o
        if a <= 0:
            continue
        put(layer, label_icon(kind, t), GX0 + 22, 250 + dy, s, a)
        put(layer, txt(text, 40, "Bold"), GX0 + 58, 250 + dy, s, a, ax=0)


# ---------------------------------------------------------------- rounds

R1_CARDS = [
    dict(title=[("跟", 4), ("老", 5), ("板", 6), ("过", 7), ("方", 8), ("案", 9)],
         tags=[("clock", "明天 10:00", [0, 1, 2, 3]), ("bell", "提前 15 分钟提醒", [])]),
    dict(title=[("改", 15), (" ", None), ("PPT", 11)], tags=[("clock", "今晚 22:00 前", [12, 13])]),
]
R2_CARDS = [
    dict(title=[("妈", None), ("妈", 3), ("生", 4), ("日", 5)], tags=[("clock", "周六 · 全天", [0, 1])]),
    dict(title=[("订", 8), ("蛋", 10), ("糕", 11)], tags=[("clock", "周六前", []), ("bell", "周五提醒你", [])]),
    dict(title=[("游", 25), ("泳", 26)],
         tags=[("clock", "每周二、四 19:30", list(range(15, 24))), ("repeat", "每周重复", [])]),
    dict(title=[("交", 32), ("房", 28), ("租", 29)], tags=[("clock", "周日前", [30, 31])]),
]


def make_round(groups, typ, marks_t, blow, reflow, task, tags_t, checks, cards, out):
    cells, marks, kept = build(groups)
    return dict(cells=cells, marks=marks, kept=kept, typ=type_times(cells, typ), marks_t=marks_t, blow=blow,
                reflow=reflow, task=task, tags_t=tags_t, checks=checks, cards=cards, out=out)


RD1 = make_round(R1_GROUPS, TYPE1, MARK1, BLOW1, REFLOW1, TASK1, TAGS1, CHECKS1, R1_CARDS, OUT1)
RD2 = make_round(R2_GROUPS, TYPE2, MARK2, BLOW2, REFLOW2, TASK2, TAGS2, CHECKS2, R2_CARDS, CAL)


def grid_cell_alpha(i, t):
    if t < TASK1 + 0.4:
        return 1 - prog(t, TASK1 - 0.05, 0.3)
    if t < AGAIN:
        return 0.0
    r, c = divmod(i, COLS)
    return prog(t, AGAIN + 0.1 + (r + c) * 0.016, 0.18) * (1 - prog(t, TASK2 - 0.05, 0.3))


def draw_grid(layer, t, active=None):
    base = cell_img(CELL)
    for i in range(56):
        a = grid_cell_alpha(i, t)
        if a <= 0:
            continue
        x, y = cell_center(i)
        put(layer, base if a > 0.99 else fade_img(base, a), x, y)
    if active is not None and active < 56:
        x, y = cell_center(active)
        put(layer, cell_img(CELL, CELL_FILL, ORANGE, 3), x, y)


@lru_cache(64)
def marked_sprite(s):
    img = Image.new("RGBA", (CELL + 4, CELL + 4), (0, 0, 0, 0))
    img.alpha_composite(cell_img(CELL, ROSE_SOFT, ROSE_LINE), (2, 2))
    g = glyph(s, GLYPH, ROSE)
    img.alpha_composite(g, ((img.width - g.width) // 2, (img.height - g.height) // 2))
    return img


def card_xy(k):
    return GX0, CARD_Y0 + k * CARD_STEP


@lru_cache(4)
def card_bg():
    return with_shadow(rrect(CARD_W, CARD_H, 30, WHITE + (255,), CELL_LINE + (255,), 2), blur=18, dy=10,
                       opacity=0.12)


def title_slots(card, k):
    x0, y0 = card_xy(k)
    acc, out = "", []
    for s, _ in card["title"]:
        w = text_width(s, TITLE_SIZE, "Black")
        out.append((x0 + 112 + text_width(acc, TITLE_SIZE, "Black") + w / 2, y0 + 56))
        acc += s
    return out


def tag_slots(card, k):
    x0, y0 = card_xy(k)
    x, out = x0 + 112, []
    for kind, text, _ in card["tags"]:
        img = tag_img(kind, text)
        out.append((x + img.width / 2, y0 + 112))
        x += img.width + 12
    return out


def card_start(rd, k):
    return rd["task"] - 0.05 + 0.07 * k


def round_flights(rd):
    """Per clean-glyph destination: ('title', card, slot) | ('tag', card, slot) | None."""
    dest = {}
    for k, card in enumerate(rd["cards"]):
        for j, (_, src) in enumerate(card["title"]):
            if src is not None:
                dest[src] = ("title", k, j)
        for j, (_, _, srcs) in enumerate(card["tags"]):
            for src in srcs:
                dest[src] = ("tag", k, j)
    return dest


def draw_round(layer, t, rd, typing_active=True):
    cells, marks, kept = rd["cells"], rd["marks"], rd["kept"]
    typ = rd["typ"]
    task, blow, reflow = rd["task"], rd["blow"], rd["reflow"]
    typed = sum(1 for tt in typ if t >= tt)
    active = typed if typing_active and typ[0] - 0.15 <= t < typ[-1] + 0.25 else None
    draw_grid(layer, t, active)

    mark_of = {}
    for gi, (s, n, kind) in enumerate(marks):
        for i in range(s, s + n):
            mark_of[i] = gi

    # removed glyphs: mark, then blow away
    for i, s in enumerate(cells):
        if i not in mark_of or t < typ[i]:
            continue
        gi = mark_of[i]
        mt = rd["marks_t"][gi]
        x, y = cell_center(i)
        pop = prog(t, typ[i], 0.1)
        sc = lerp(1.3, 1, out_cubic(pop))
        if t < blow:
            m = prog(t, mt, 0.12)
            bump = 1 + 0.12 * math.sin(math.pi * prog(t, mt, 0.22))
            if m < 1:
                put(layer, glyph(s, GLYPH), x, y, sc, clamp(pop * 2) * (1 - m))
            if m > 0:
                put(layer, marked_sprite(s), x, y, bump, m)
            continue
        rnd = random.Random(i * 37 + len(cells))
        p = prog(t, blow + rnd.uniform(0, 0.12), 0.62)
        if p >= 1:
            continue
        e = out_cubic(p)
        put(layer, marked_sprite(s), x + rnd.uniform(-150, 230) * e, y + rnd.uniform(-460, -180) * e + 120 * p * p,
            1 + 0.35 * e, (1 - p) ** 1.4, rotate=rnd.uniform(-170, 170) * e)

    # mark tags
    for gi, (s0, n, kind) in enumerate(marks):
        mt = rd["marks_t"][gi]
        q = prog(t, mt, 0.3)
        if q <= 0:
            continue
        x, y = cell_center(s0)
        img = chip("口头禅" if kind == "f" else "改口", WHITE, ROSE)
        tx, ty = x - CELL / 2 + 4, y - CELL / 2 - 2
        if t < blow:
            put(layer, img, tx, ty, lerp(0.5, 1, out_back(q)), clamp(q * 3), ax=0)
        else:
            p = prog(t, blow, 0.5)
            put(layer, img, tx + 80 * p, ty - 300 * out_cubic(p), 1.0, 1 - p, ax=0, rotate=-30 * p)

    draw_cards(layer, t, rd)

    # kept glyphs: type in, reflow, then fly into cards
    dest = round_flights(rd)
    order = {src: n for n, src in enumerate(sorted(dest))}
    for k, i in enumerate(kept):
        if t < typ[i]:
            continue
        s = cells[i]
        x0, y0 = cell_center(i)
        x1, y1 = cell_center(k)
        r = in_out(prog(t, reflow + k * 0.012, 0.42))
        x, y = lerp(x0, x1, r), lerp(y0, y1, r) - 26 * math.sin(math.pi * r)
        pop = prog(t, typ[i], 0.1)
        sc = lerp(1.3, 1, out_cubic(pop))
        a = clamp(pop * 2)
        if t < task:
            put(layer, glyph(s, GLYPH), x, y, sc, a)
            continue
        d = dest.get(k)
        if d is None:
            p = prog(t, task, 0.3)
            put(layer, glyph(s, GLYPH), x, y + 40 * p, 1 - 0.2 * p, 1 - p)
            continue
        kind, ci, j = d
        f0 = task + 0.05 + order[k] * 0.022
        p = in_out(prog(t, f0, 0.5))
        if kind == "title":
            tx, ty = title_slots(rd["cards"][ci], ci)[j]
            target = text_width(s, TITLE_SIZE, "Black") / max(1.0, font("Black", glyph_size(s, GLYPH)).getlength(s))
            if p >= 1:
                continue
            put(layer, glyph(s, GLYPH), lerp(x, tx, p), lerp(y, ty, p) - 70 * math.sin(math.pi * p),
                lerp(1, target, p), 1.0)
        else:
            tx, ty = tag_slots(rd["cards"][ci], ci)[j]
            if p >= 1:
                continue
            put(layer, glyph(s, GLYPH, ORANGE), lerp(x, tx, p), lerp(y, ty, p) - 50 * math.sin(math.pi * p),
                lerp(1, 0.45, p), 1 - p ** 3)


def card_exit(rd, t, k):
    """(alpha, scale, dx, dy) applied to card k on its way out."""
    if rd is RD1:
        o = out_cubic(prog(t, rd["out"] + 0.04 * k, 0.3))
        return 1 - o, 1.0, 0, -80 * o
    o = in_out(prog(t, CAL + 0.05 * k, 0.42))
    bx, by = pill_bank()[R2_PILL[k]]
    x0, y0 = card_xy(k)
    cx, cy = x0 + CARD_W / 2, y0 + CARD_H / 2
    return 1 - prog(o, 0.4, 0.6), lerp(1, 0.3, o), (bx - cx) * o, (by - cy) * o


def draw_cards(layer, t, rd):
    if t < rd["task"] - 0.1:
        return
    dest_title_land = rd["task"] + 0.55
    for k, card in enumerate(rd["cards"]):
        a, s, dy = appear(t, card_start(rd, k), 0.4, rise=30, from_scale=0.94)
        ea, es, ex, ey = card_exit(rd, t, k)
        a *= ea
        if a <= 0:
            continue
        sub = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bg, pad = card_bg()
        x0, y0 = card_xy(k)
        sub.alpha_composite(bg, (x0 - pad, y0 - pad))
        ct = rd["checks"][k]
        q = prog(t, ct, 0.3)
        if q < 1:
            put(sub, ring(22, 3, CELL_LINE + (255,)), x0 + 60, y0 + 56)
        if q > 0:
            put(sub, check_badge(50), x0 + 60, y0 + 56, lerp(0.4, 1, out_back(q)), clamp(q * 3))
        for j, ((g, src), (tx, ty)) in enumerate(zip(card["title"], title_slots(card, k))):
            if g == " ":
                continue
            if src is None:
                pa = prog(t, dest_title_land + 0.05, 0.25)
                put(sub, glyph(g, TITLE_SIZE, fit=False), tx, ty, lerp(0.4, 1, out_back(pa)), clamp(pa * 3))
            else:
                order = sorted(round_flights(rd)).index(src)
                if prog(t, rd["task"] + 0.05 + order * 0.022, 0.5) >= 1:
                    put(sub, glyph(g, TITLE_SIZE, fit=False), tx, ty)
        for j, ((kind, text, _), (tx, ty)) in enumerate(zip(card["tags"], tag_slots(card, k))):
            pa = prog(t, rd["tags_t"] + 0.12 * k + 0.06 * j, 0.32)
            if pa > 0:
                put(sub, tag_img(kind, text), tx, ty, lerp(0.6, 1, out_back(pa)), clamp(pa * 3))
        blit_card(layer, sub, x0, y0, s, es, ex, dy + ey, a)


def blit_card(layer, sub, x0, y0, s, es, ex, ey, a):
    box = (x0 - 60, y0 - 60, x0 + CARD_W + 60, y0 + CARD_H + 80)
    crop = sub.crop(box)
    cx = (box[0] + box[2]) / 2 + ex
    cy = (box[1] + box[3]) / 2 + ey
    put(layer, crop, cx, cy, s * es, a)


# ---------------------------------------------------------------- counters & lines

COUNTERS = [("去口头禅", "f"), ("改口纠正", "c"), ("拆成待办", "task"), ("填好时间", "time")]


def counter_events():
    ev = {"f": [], "c": [], "task": [], "time": []}
    for rd in (RD1, RD2):
        for (s, n, kind), mt in zip(rd["marks"], rd["marks_t"]):
            ev[kind].append(mt)
        ev["task"] += rd["checks"]
        ev["time"] += [rd["tags_t"] + 0.12 * k for k in range(len(rd["cards"]))]
    return ev


CEV = counter_events()


def draw_counters(layer, t):
    a = 1 - prog(t, CAL, 0.25)
    if a <= 0:
        return
    for k, (label, key) in enumerate(COUNTERS):
        times = [x for x in CEV[key] if x <= t]
        n = len(times)
        last = max(times) if times else -9
        hl = 1 - prog(t, last + 0.25, 0.45)
        color, soft = (ROSE, ROSE_SOFT) if key in ("f", "c") else (ORANGE, ORANGE_SOFT)
        x = GX0 + k * 228 + 110
        y = 1255
        put(layer, rrect(220, 130, 20, CELL_FILL + (255,), CELL_LINE + (255,), 2), x, y, 1.0, a)
        if hl > 0 and n:
            put(layer, rrect(220, 130, 20, soft + (255,), color + (255,), 3), x, y, 1.0, a * hl)
        put(layer, txt(label, 26, "Medium", MUTED), x, y - 26, 1.0, a)
        vc = color if hl > 0.3 and n else (INK if n else (200, 192, 184))
        pop = 1 + 0.3 * (1 - prog(t, last, 0.25)) if n else 1.0
        put(layer, txt(f"×{n}", 52, "Black", vc), x, y + 24, pop, a)


def draw_line(layer, t, t_in, t_out, lines, y0=1450, size=60, gap=86):
    o = prog(t, t_out, 0.25)
    for k, segs in enumerate(lines):
        a, s, dy = appear(t, t_in + 0.12 * k, rise=36)
        if a <= 0:
            continue
        put(layer, rich(segs, size, "Black"), 540, y0 + k * gap + dy - 40 * o, s, a * (1 - o))


# ---------------------------------------------------------------- climax: calendar

CAL_COLW, CAL_PITCH = 122, 130
ROW_Y = [330, 430, 552, 648, 744, 840, 936, 1032]
ROW_H = [90, 110, 88, 88, 88, 88, 88, 88]
DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
DATES = [12, 13, 14, 15, 16, 17, 18]
TODAY = 1

PILLS = ["过方案", "改 PPT", "妈妈生日", "订蛋糕", "游泳", "交房租"]
R2_PILL = [2, 3, 4, 5]
BLOCKS = [("过方案", "10:00", 2, 2, 0), ("改 PPT", "22:00", 1, 7, 1), ("妈妈生日", "全天", 5, None, 2),
          ("订蛋糕", "周六前", 4, None, 3), ("游泳", "19:30", 1, 6, 4), ("游泳", "19:30", 3, 6, 4),
          ("交房租", "截止", 6, None, 5)]


@lru_cache(1)
def pill_bank():
    out = []
    for row, names in enumerate((PILLS[:3], PILLS[3:])):
        ws = [pill_img(n).width for n in names]
        total = sum(ws) + 18 * (len(ws) - 1)
        x = 540 - total / 2
        for w in ws:
            out.append((x + w / 2, 1440 + row * 92))
            x += w + 18
    return out


@lru_cache(16)
def pill_img(name):
    w = int(text_width(name, 30, "Bold")) + 76
    img = rrect(w, 66, 33, WHITE + (255,), CELL_LINE + (255,), 2).copy()
    put(img, circle_dot(), 30, 33)
    put(img, txt(name, 30, "Bold"), 48, 33, ax=0)
    return with_shadow(img, blur=12, dy=6, opacity=0.12)[0]


@lru_cache(1)
def circle_dot():
    return R.circle(14, ORANGE + (255,))


def cal_rect(j):
    c, r = j % 7, j // 7
    return GX0 + c * CAL_PITCH, ROW_Y[r], CAL_COLW, ROW_H[r]


def grid_rect(i):
    c, r = i % COLS, i // COLS
    return GX0 + c * PITCH, GY0 + r * PITCH, CELL, CELL


def block_rect(b):
    _, _, col, row, _ = BLOCKS[b]
    x = GX0 + col * CAL_PITCH + 4
    if row is None:
        return x, ROW_Y[1] + 8, 114, 94
    return x, ROW_Y[row] + 8, 114, 72


@lru_cache(8)
def block_img(b):
    title, when, _, hour, _ = BLOCKS[b]
    _, _, w, h = block_rect(b)
    h = int(h)
    img = rrect(w, h, 10, ORANGE_SOFT + (255,)).copy()
    put(img, rrect(5, h - 18, 3, ORANGE + (255,)), 8, h / 2)
    ty = 26 if hour is not None else 32
    put(img, txt(title, 23, "Bold"), 17, ty, ax=0)
    put(img, txt(when, 19, "Bold", ORANGE), 17, ty + (26 if hour is not None else 32), ax=0)
    return img


def draw_calendar(layer, t):
    out = prog(t, CAL_OUT, 0.32)
    sub = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(sub)
    appear_a = prog(t, MORPH - 0.15, 0.2)
    if appear_a > 0:
        for i in range(56):
            p = in_out(prog(t, MORPH + i * MORPH_STAGGER, MORPH_DUR))
            g, c = grid_rect(i), cal_rect(i)
            x, y, w, h = (lerp(a, b, p) for a, b in zip(g, c))
            row = i // 7
            line = ORANGE if (p > 0.95 and row == 0 and i % 7 == TODAY) else CELL_LINE
            draw_rect(d, x, y, w, h, CELL_FILL + (int(255 * appear_a),), line + (int(255 * appear_a),),
                      3 if line == ORANGE else 2)
    for c in range(7):
        q = prog(t, CAL_HEAD + 0.04 * c, 0.3)
        if q <= 0:
            continue
        x, y, w, h = cal_rect(c)
        cx = x + w / 2
        put(sub, txt(DAYS[c], 22, "Medium", MUTED), cx, y + 22 + 10 * (1 - out_cubic(q)), 1.0, q)
        if c == TODAY:
            put(sub, R.circle(44, ORANGE + (255,)), cx, y + 62, lerp(0.5, 1, out_back(q)), q)
            put(sub, txt(str(DATES[c]), 30, "Black", WHITE), cx, y + 62, 1.0, q)
        else:
            put(sub, txt(str(DATES[c]), 30, "Black"), cx, y + 62 + 10 * (1 - out_cubic(q)), 1.0, q)

    # pills: R2 cards shrink into them; R1 ones drop in from above
    for n, name in enumerate(PILLS):
        firsts = [LAND[b] for b, blk in enumerate(BLOCKS) if blk[4] == n]
        if t >= min(firsts):
            continue
        bx, by = pill_bank()[n]
        if n < 2:
            a, s, dy = appear(t, CAL + 0.1 + 0.08 * n, 0.4, rise=-70)
        else:
            k = R2_PILL.index(n)
            q = prog(t, CAL + 0.05 * k + 0.2, 0.25)
            a, s, dy = q, lerp(0.7, 1, out_back(q)), 0
        put(sub, pill_img(name), bx, by + dy, s, a)

    for b, (title, when, col, hour, n) in enumerate(BLOCKS):
        p = prog(t, LAND[b], FLY_DUR)
        if p <= 0:
            continue
        x, y, w, h = block_rect(b)
        tx, ty = x + w / 2, y + h / 2
        bx, by = pill_bank()[n]
        e = in_out(p)
        if p < 1:
            cx, cy = lerp(bx, tx, e), lerp(by, ty, e) - 120 * math.sin(math.pi * e)
            put(sub, pill_img(PILLS[n]), cx, cy, lerp(1, 0.6, e), 1 - e)
            put(sub, block_img(b), cx, cy, lerp(0.5, 1, e), e)
        else:
            land = prog(t, LAND[b] + FLY_DUR, 0.3)
            put(sub, block_img(b), tx, ty, 1 + 0.12 * math.sin(math.pi * land))
            if land < 1:
                flash = rrect(w + 8, int(h) + 8, 12, (255, 255, 255, 0), ORANGE + (255,), 3)
                put(sub, flash, tx, ty, 1 + 0.15 * land, 1 - land)

    shake = 0.0
    for s0 in SLAM:
        if t > s0:
            u = t - s0
            shake += 9 * math.sin(u * 70) * math.exp(-u * 12)
    lines = [((("说得再乱，", INK),), 1440), ((("日程也", INK), ("井井有条", ORANGE), ("。", INK)), 1556)]
    for (segs, y), s0 in zip(lines, SLAM):
        q = prog(t, s0, 0.16)
        if q <= 0:
            continue
        put(sub, rich(segs, 84, "Black"), 540, y, lerp(1.7, 1, out_cubic(q)), clamp(q * 2.5))
    put(layer, sub, 540, 960 + shake - 110 * out_cubic(out), 1.0, 1 - out)


# ---------------------------------------------------------------- slogan row & end card

END_DY = 177
ROW_Y_END = 739 + END_DY
SL_CELLS = cells_of(SLOGAN_TEXT)
PRE_SIZE, PRE_PITCH = 76, 82
END_SIZE, END_PITCH = 99, 104
CHIP_ROWS = [[(245, 438, "phone", "iPhone"), (458, 666, "phone", "Android"), (686, 835, "laptop", "Mac")],
             [(281, 506, "laptop", "Windows"), (526, 799, "watch", "Apple Watch")]]
CHIP_YS = [990 + END_DY, 1080 + END_DY]


def pre_x(i):
    return 540 - (len(SL_CELLS) * PRE_PITCH - 6) / 2 + i * PRE_PITCH + PRE_SIZE / 2


def end_x(k):
    return 176 + k * END_PITCH + END_SIZE / 2


@lru_cache(8)
def device_chip(x0, x1, icon, label):
    w = x1 - x0 + 1
    img = rrect(w, 65, 32, CELL_FILL + (255,), ORANGE + (255,), 3).copy()
    tw = text_width(label, 32, "Bold")
    content = 26 + 12 + tw
    left = (w - content) / 2
    put(img, tag_icon(icon, 26, ORANGE), left + 13, 32)
    put(img, txt(label, 32, "Bold"), left + 38, 33, ax=0)
    return img


def draw_slogan(layer, t):
    typ = type_times(SL_CELLS, TYPE3)
    sub = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(sub)
    kept = list(range(SLOGAN_DROP, len(SL_CELLS)))
    for i, s in enumerate(SL_CELLS):
        ca = prog(t, TYPE3[0] - 0.12 + i * 0.025, 0.2)
        if ca <= 0:
            continue
        cs = lerp(0.6, 1, out_back(ca))
        typed = t >= typ[i]
        gp = prog(t, typ[i], 0.1)
        if i < SLOGAN_DROP:
            m = prog(t, MARK3, 0.12)
            if t < BLOW3:
                x, y = pre_x(i), ROW_Y_END
                size = PRE_SIZE * cs
                fill = tuple(int(lerp(a, b, m)) for a, b in zip(CELL_FILL, ROSE_SOFT))
                line = tuple(int(lerp(a, b, m)) for a, b in zip(CELL_LINE, ROSE_LINE))
                draw_rect(d, x - size / 2, y - size / 2, size, size, fill + (int(255 * ca),), line + (int(255 * ca),))
                if typed:
                    col = ROSE if m > 0.5 else INK
                    put(sub, glyph(s, 46, col), x, y, lerp(1.3, 1, out_cubic(gp)), clamp(gp * 2))
            else:
                rnd = random.Random(i * 13 + 5)
                p = prog(t, BLOW3 + rnd.uniform(0, 0.08), 0.55)
                if p < 1:
                    e = out_cubic(p)
                    spr = Image.new("RGBA", (PRE_SIZE + 4, PRE_SIZE + 4), (0, 0, 0, 0))
                    spr.alpha_composite(cell_img(PRE_SIZE, ROSE_SOFT, ROSE_LINE), (2, 2))
                    g = glyph(s, 46, ROSE)
                    spr.alpha_composite(g, ((spr.width - g.width) // 2, (spr.height - g.height) // 2))
                    put(sub, spr, pre_x(i) + rnd.uniform(-120, 160) * e, ROW_Y_END + rnd.uniform(-380, -160) * e,
                        1 + 0.3 * e, (1 - p) ** 1.4, rotate=rnd.uniform(-160, 160) * e)
            continue
        k = i - SLOGAN_DROP
        r = in_out(prog(t, REFLOW3 + k * 0.02, 0.45))
        x = lerp(pre_x(i), end_x(k), r)
        size = lerp(PRE_SIZE, END_SIZE, r) * cs
        hl = prog(t, ORANGE3[k - 4], 0.2) if k >= 4 else 0
        bump = 1 + 0.14 * math.sin(math.pi * hl) if k >= 4 else 1
        size *= bump
        fill = tuple(int(lerp(a, b, hl)) for a, b in zip(CELL_FILL, ORANGE_SOFT))
        line = tuple(int(lerp(a, b, hl)) for a, b in zip(CELL_LINE, ORANGE))
        draw_rect(d, x - size / 2, ROW_Y_END - size / 2, size, size, fill + (int(255 * ca),), line + (int(255 * ca),),
                  3 if hl > 0.5 else 2)
        if typed:
            gs = lerp(46 / 62, 1, r) * bump * lerp(1.3, 1, out_cubic(gp))
            col = ORANGE if hl > 0.5 else INK
            put(sub, glyph(s, 62, col, "Bold"), x, ROW_Y_END, gs, clamp(gp * 2))
    if t < BLOW3 + 0.5:
        q = prog(t, MARK3, 0.3)
        if q > 0:
            p = prog(t, BLOW3, 0.5)
            put(sub, chip("口头禅", WHITE, ROSE), pre_x(0) - PRE_SIZE / 2 + 2 + 60 * p,
                ROW_Y_END - PRE_SIZE / 2 - 2 - 260 * out_cubic(p), lerp(0.5, 1, out_back(q)), clamp(q * 3) * (1 - p),
                ax=0)
    layer.alpha_composite(sub)


def draw_end(layer, t):
    a, s, dy = appear(t, LOGO, 0.5, rise=40, from_scale=0.5)
    if a > 0:
        put(layer, logo_tile(), 540, 400 + END_DY + dy, s, a)
    a, s, dy = appear(t, TITLE, rise=36)
    put(layer, txt("闪念贝壳", 86, "Black"), 540, 584 + END_DY + dy, s, a)
    a, s, dy = appear(t, TAGLINE, rise=30)
    put(layer, txt("任何设备，随时同步", 42, "Bold"), 540, 902 + END_DY + dy, s, a)
    k = 0
    for row, y in zip(CHIP_ROWS, CHIP_YS):
        for x0, x1, icon, label in row:
            a, s, dy = appear(t, CHIPS[k], 0.4, rise=24, from_scale=0.6)
            put(layer, device_chip(x0, x1, icon, label), (x0 + x1) / 2, y + dy, s, a)
            k += 1
    a, s, dy = appear(t, STORE, rise=20)
    put(layer, txt("应用商店搜「闪念贝壳」", 32, "Bold", MUTED), 540, 1251 + END_DY + dy, s, a)


@lru_cache(1)
def logo_tile():
    return with_shadow(asset("logo", height=196), blur=16, dy=8, opacity=0.1)[0]


# ---------------------------------------------------------------- frame

def render(t):
    img = Image.new("RGBA", (W, H), PAPER + (255,))
    draw_header(img, t)
    draw_label(img, t)
    if t < CAL + 0.6:
        rd = RD1 if t < AGAIN else RD2
        draw_round(img, t, rd)
    draw_counters(img, t)
    draw_line(img, t, LINE1, OUT1, [(("说完，就变成", INK), ("待办", ORANGE), ("。", INK))])
    draw_line(img, t, LINE2, CAL, [(("口头禅、改口都不怕，", INK),), (("时间和提醒自动填好。", ORANGE),)],
              y0=1420, size=50, gap=78)
    if CAL <= t < CAL_OUT + 0.4:
        draw_calendar(img, t)
    if t >= TYPE3[0] - 0.2:
        draw_slogan(img, t)
        draw_end(img, t)
    return img.convert("RGB")


def render_frame(i):
    return render(i / FPS).tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", nargs="*", type=float)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    if args.stills:
        for t in args.stills:
            path = os.path.join(OUT_DIR, f"s-still-{t:05.2f}.png")
            render(t).save(path)
            print(path)
        return
    n = int(DURATION * FPS)
    out = os.path.join(OUT_DIR, "schedule-video.mp4")
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
