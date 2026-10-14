"""Render the ideaShell 9:16 promo as frames piped into ffmpeg.

    python3 render.py                 # full video -> out/video.mp4 (no audio)
    python3 render.py --stills 3 9.5  # PNG stills -> out/still-*.png
"""

import argparse
import math
import os
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from timeline import *  # noqa: F403

ROOT = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(ROOT, "fonts")
ASSET_DIR = os.path.join(ROOT, "assets")
OUT_DIR = os.path.join(ROOT, "out")
SS = 2


# ---------- easing ----------

def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def prog(t, start, dur):
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


def out_cubic(p):
    return 1 - (1 - p) ** 3


def in_cubic(p):
    return p ** 3


def in_out(p):
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def out_back(p, s=1.9):
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def lerp(a, b, p):
    return a + (b - a) * p


def appear(t, t0, dur=0.42, rise=46, from_scale=0.72):
    """Standard pop-in: returns (alpha, scale, dy)."""
    p = prog(t, t0, dur)
    if p <= 0:
        return 0.0, from_scale, rise
    return clamp(p * 2.2), lerp(from_scale, 1.0, out_back(p)), rise * (1 - out_cubic(p))


# ---------- drawing primitives ----------

LATIN = os.environ.get("VIDEO_LANG", "zh") == "en"
# Inter has a shorter ascender than Noto SC, so it needs a taller box to keep descenders.
BOX_H, BASELINE = (1.0, 0.97) if LATIN else (0.86, 0.93)


@lru_cache(64)
def font(weight, size):
    name = f"Inter-{weight}.ttf" if LATIN else f"NotoSansSC-{weight}.otf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


@lru_cache(4096)
def rich(segments, size, weight="Bold"):
    f = font(weight, size)
    asc, desc = f.getmetrics()
    width = sum(f.getlength(s) for s, _ in segments)
    img = Image.new("RGBA", (math.ceil(width) + 4, int((asc + desc) * BOX_H) + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 2
    for s, color in segments:
        d.text((x, 2 + asc * BASELINE), s, font=f, fill=color, anchor="ls")
        x += f.getlength(s)
    return img


def txt(s, size, weight="Bold", color=INK):
    return rich(((s, color),), size, weight)


def text_width(s, size, weight="Bold"):
    return font(weight, size).getlength(s)


@lru_cache(512)
def rrect(w, h, r, fill, outline=None, width=0):
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(
        (0, 0, w * SS - 1, h * SS - 1), r * SS, fill=fill, outline=outline, width=width * SS
    )
    return img.resize((w, h), Image.LANCZOS)


@lru_cache(256)
def circle(d, fill, outline=None, width=0):
    img = Image.new("RGBA", (d * SS, d * SS), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((0, 0, d * SS - 1, d * SS - 1), fill=fill, outline=outline, width=width * SS)
    return img.resize((d, d), Image.LANCZOS)


@lru_cache(256)
def ring(r, width, color):
    d = 2 * r + 2 * width
    img = Image.new("RGBA", (d * SS, d * SS), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((0, 0, d * SS - 1, d * SS - 1), outline=color, width=width * SS)
    return img.resize((d, d), Image.LANCZOS)


@lru_cache(64)
def check_icon(size, color, width):
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pts = [(0.2 * s, 0.53 * s), (0.42 * s, 0.74 * s), (0.8 * s, 0.3 * s)]
    ImageDraw.Draw(img).line(pts, fill=color, width=width * SS, joint="curve")
    d = ImageDraw.Draw(img)
    for x, y in (pts[0], pts[-1]):
        rr = width * SS / 2
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=color)
    return img.resize((size, size), Image.LANCZOS)


@lru_cache(64)
def check_badge(d, fill=ORANGE, mark=WHITE):
    img = circle(d, fill).copy()
    icon = check_icon(int(d * 0.72), mark, max(3, d // 11))
    img.alpha_composite(icon, ((d - icon.width) // 2, (d - icon.height) // 2 + 1))
    return img


@lru_cache(64)
def sparkle(size, color):
    s = size * SS
    c = s / 2
    pts = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        r = c if i % 2 == 0 else c * 0.28
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon(pts, fill=color)
    return img.resize((size, size), Image.LANCZOS)


@lru_cache(16)
def spinner(d, color):
    img = Image.new("RGBA", (d * SS, d * SS), (0, 0, 0, 0))
    w = max(3, d // 10) * SS
    dr = ImageDraw.Draw(img)
    dr.ellipse((0, 0, d * SS - 1, d * SS - 1), outline=LINE, width=w)
    dr.arc((0, 0, d * SS - 1, d * SS - 1), -90, 30, fill=color, width=w)
    return img.resize((d, d), Image.LANCZOS)


@lru_cache(16)
def mic_icon(size, color):
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = int(s * 0.09)
    d.rounded_rectangle((s * 0.34, s * 0.08, s * 0.66, s * 0.62), s * 0.16, fill=color)
    d.arc((s * 0.2, s * 0.26, s * 0.8, s * 0.76), 0, 180, fill=color, width=w)
    d.line((s * 0.5, s * 0.76, s * 0.5, s * 0.92), fill=color, width=w)
    return img.resize((size, size), Image.LANCZOS)


@lru_cache(16)
def glow(d, color, opacity):
    img = Image.new("RGBA", (d, d), color + (0,))
    a = Image.new("L", (d, d), 0)
    ImageDraw.Draw(a).ellipse((d * 0.25, d * 0.25, d * 0.75, d * 0.75), fill=int(255 * opacity))
    img.putalpha(a.filter(ImageFilter.GaussianBlur(d * 0.12)))
    return img


def with_shadow(img, blur=26, dy=16, opacity=0.14, color=(70, 45, 20)):
    pad = blur * 2 + abs(dy)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, color + (0,))
    sh.putalpha(img.getchannel("A").point(lambda v: int(v * opacity)))
    out.alpha_composite(sh, (pad, pad + dy))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(img, (pad, pad))
    return out, pad


@lru_cache(32)
def card_base(w, h, r=40, fill=WHITE, outline=None, width=0, shadow=(70, 45, 20), opacity=0.14):
    return with_shadow(rrect(w, h, r, fill, outline, width), color=shadow, opacity=opacity)


class Card:
    """A shadowed card that is composed per frame, then placed with put()."""

    def __init__(self, w, h, **kw):
        base, self.pad = card_base(w, h, **kw)
        self.img = base.copy()
        self.w, self.h = w, h

    def add(self, img, x, y, ax=0.0, ay=0.0, alpha=1.0, scale=1.0, rotate=0.0):
        put(self.img, img, self.pad + x, self.pad + y, scale=scale, alpha=alpha, ax=ax, ay=ay, rotate=rotate)

    def draw(self):
        return ImageDraw.Draw(self.img), self.pad


@lru_cache(32)
def asset(name, height=None, width=None):
    img = Image.open(os.path.join(ASSET_DIR, name + ".png")).convert("RGBA")
    if height or width:
        k = height / img.height if height else width / img.width
        img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
    return img


@lru_cache(8)
def asset_shadowed(name, height):
    return with_shadow(asset(name, height=height), blur=30, dy=24, opacity=0.18)[0]


def with_alpha(img, alpha):
    if alpha >= 0.999:
        return img
    img = img.copy()
    img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    return img


def put(dst, img, x, y, scale=1.0, alpha=1.0, ax=0.5, ay=0.5, rotate=0.0):
    if alpha <= 0.004 or scale <= 0.02:
        return
    if abs(scale - 1) > 1e-3:
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.BICUBIC)
    if abs(rotate) > 0.05:
        img = img.rotate(rotate, Image.BICUBIC, expand=True)
    img = with_alpha(img, alpha)
    x = round(x - img.width * ax)
    y = round(y - img.height * ay)
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(img.width, dst.width - x), min(img.height, dst.height - y)
    if ex <= sx or ey <= sy:
        return
    if (sx, sy, ex, ey) != (0, 0, img.width, img.height):
        img = img.crop((sx, sy, ex, ey))
    dst.alpha_composite(img, (x + sx, y + sy))


# ---------- xiaohongshu safe area ----------

# Xiaohongshu shows 9:16 video under the status bar and back/share icons, and crops ~70px off each side.
XHS_TOP, XHS_SCALE = 205, 0.86


def xhs_safe(img, bg):
    """Shrink a full-bleed layout around the center and push it below the top band."""
    w, h = img.size
    sw, sh = round(w * XHS_SCALE), round(h * XHS_SCALE)
    out = Image.new("RGB", (w, h), bg)
    out.paste(img.convert("RGB").resize((sw, sh), Image.LANCZOS).crop((0, 0, sw, min(sh, h - XHS_TOP))),
              ((w - sw) // 2, XHS_TOP))
    return out


# ---------- background ----------

GRID = 44


@lru_cache(1)
def grid_sheet():
    img = Image.new("RGBA", (W, H + GRID), PAPER + (255,))
    d = ImageDraw.Draw(img)
    for y in range(0, H + GRID, GRID):
        for x in range(GRID // 2, W, GRID):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(221, 214, 203, 255))
    return img


def background(t):
    off = int(t * 14) % GRID
    frame = grid_sheet().crop((0, off, W, off + H)).copy()
    gx = 540 + 300 * math.sin(t * 0.35)
    gy = 760 + 260 * math.cos(t * 0.27)
    put(frame, glow(1400, ORANGE, 0.10), gx, gy)
    return frame


# ---------- shared scene pieces ----------

def stage_pill(label, active):
    size = 36
    w = int(text_width(label, size)) + 64
    if active:
        base = rrect(w, 76, 38, ORANGE + (255,))
        t = txt(label, size, "Bold", WHITE)
    else:
        base = rrect(w, 76, 38, WHITE + (255,), LINE + (255,), 2)
        t = txt(label, size, "Bold", GRAY)
    img = base.copy()
    put(img, t, w / 2, 38)
    return img


def stepper(layer, t, t0, ji_on, xiang_on, y=462):
    a, s, dy = appear(t, t0 + 0.18)
    pills = [("记 · 录下来", ji_on), ("想 · 一起想", xiang_on)]
    xs = [540 - 175, 540 + 175]
    d = ImageDraw.Draw(layer)
    if a > 0:
        lc = LINE + (int(255 * a),)
        d.line((540 - 40, y + dy, 540 + 30, y + dy), fill=lc, width=4)
        d.line((540 + 16, y + dy - 14, 540 + 32, y + dy, 540 + 16, y + dy + 14), fill=lc, width=4)
    for (label, on_t), x in zip(pills, xs):
        p = prog(t, on_t, 0.3)
        bump = 1 + 0.14 * math.sin(math.pi * p)
        put(layer, stage_pill(label, False), x, y + dy, s, a * (1 - p))
        put(layer, stage_pill(label, True), x, y + dy, s * bump, a * p)


def header(layer, t, t0, num, name, title, ji_on, xiang_on):
    a, s, dy = appear(t, t0 + 0.02)
    chip_label = f"场景 {num}  ·  {name}"
    w = int(text_width(chip_label, 34)) + 56
    chip = rrect(w, 64, 32, ORANGE_SOFT + (255,)).copy()
    put(chip, txt(chip_label, 34, "Bold", ORANGE), w / 2, 32)
    put(layer, chip, 540, 190 + dy, s, a)
    a2, s2, dy2 = appear(t, t0 + 0.1)
    put(layer, rich(title, 84, "Black"), 540, 318 + dy2, s2, a2)
    stepper(layer, t, t0, ji_on, xiang_on)


def wrap(text, size, maxw, weight="Bold"):
    lines, cur = [], ""
    for ch in text:
        if text_width(cur + ch, size, weight) > maxw and cur:
            lines.append(cur)
            cur = ch.lstrip()
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


# ---------- scenes ----------

def scene_hook(layer, t):
    fragments = [
        (250, 470, -6, "周五要交什么来着？"),
        (820, 600, 5, "客户刚才那句…"),
        (240, 1330, 4, "一个好点子，忘了"),
        (830, 1460, -5, "回头再整理吧"),
    ]
    for i, (x, y, rot, label) in enumerate(fragments):
        p_in = prog(t, 0.03 + i * 0.1, 0.3)
        fade = 1 - 0.75 * prog(t, 0.45 + i * 0.1, 1.1)
        w = int(text_width(label, 36, "Medium")) + 56
        chip = rrect(w, 72, 36, WHITE + (255,), LINE + (255,), 2).copy()
        put(chip, txt(label, 36, "Medium", GRAY), w / 2, 36)
        put(layer, chip, x, y - 70 * t, 0.9 + 0.1 * out_cubic(p_in), p_in * fade, rotate=rot)

    lines = [
        ((("想法很多，", INK),), 0),
        ((("", INK), ("记", ORANGE), ("下的很少，", INK)), 1),
        ((("", INK), ("想透", ORANGE), ("的更少。", INK)), 2),
    ]
    for segs, i in lines:
        p = prog(t, HOOK_LINES[i], 0.28)
        if p <= 0:
            continue
        scale = lerp(1.35, 1.0, out_cubic(p))
        put(layer, rich(segs, 118, "Black"), 540, 790 + i * 160, scale, clamp(p * 2.5))


def capture_layout(widths, gap, maxw, lh):
    pos, x, y = [], 0, 0
    for w in widths:
        if x > 0 and x + w > maxw:
            x, y = 0, y + lh
        pos.append((x, y))
        x += w + gap
    return pos


CAP_SIZE, CAP_LH, CAP_MAXW = 50, 74, 840
CAP_TOP = 1065
CAP_PAD = 104


@lru_cache(1)
def capture_geometry():
    words = [w for w, _, _, _ in CAPTURE_TOKENS]
    widths = [txt(w, CAP_SIZE).width for w in words]
    messy = capture_layout(widths, 16, CAP_MAXW, CAP_LH)
    keep = [i for i, (_, k, _, _) in enumerate(CAPTURE_TOKENS) if k == "n"]
    clean_pos = capture_layout([widths[i] for i in keep], -4, CAP_MAXW, CAP_LH)
    clean = dict(zip(keep, clean_pos))
    clean_h = max(y for _, y in clean_pos) + CAP_LH
    n_messy = sum(len(w.replace(" ", "")) for w in words)
    n_clean = sum(len(words[i].replace(" ", "")) for i in keep)
    fillers = [i for i, (_, k, _, _) in enumerate(CAPTURE_TOKENS) if k == "f"]
    return words, widths, messy, clean, clean_h, n_messy, n_clean, fillers


def label_chip(label, color, fill, size=30):
    w = int(text_width(label, size)) + 40
    chip = rrect(w, size + 26, (size + 26) // 2, fill + (255,)).copy()
    put(chip, txt(label, size, "Bold", color), w / 2, (size + 26) / 2)
    return chip


def scene_capture(layer, t):
    t0 = scene_start("capture")
    a, s, dy = appear(t, t0 + 0.02)
    put(layer, rich((("抬手就", INK), ("记", ORANGE)), 128, "Black"), 540, 215 + dy, s, a)
    a, s, dy = appear(t, t0 + 0.12)
    put(layer, txt("手表、手机、电脑，开口就能记", 44, "Medium", GRAY), 540, 345 + dy, s, a)

    wa, ws, wdy = appear(t, t0 + 0.2, dur=0.55, rise=100, from_scale=0.8)
    cx, cy = 540, 705
    if wa > 0:
        talking = VOICE_AT <= t < VOICE_END
        for k in range(3):
            phase = ((t - t0) / (0.9 if talking else 1.5) + k / 3) % 1.0
            r = int(lerp(170, 380, phase)) // 4 * 4
            put(layer, ring(r, 4, ORANGE + (255,)), cx - 4, cy + 6 + wdy, 1.0, wa * 0.55 * (1 - phase) ** 1.5)
        breathe = 1 + 0.008 * math.sin((t - t0) * 6)
        put(layer, asset_shadowed("watch-zh", 560), cx, cy + wdy, ws * breathe, wa)

    ca, cs, cdy = appear(t, VOICE_AT - 0.25, rise=60)
    if ca <= 0:
        return
    words, widths, messy, clean, clean_h, n_messy, n_clean, fillers = capture_geometry()
    pc = in_out(prog(t, CAPTURE_COLLAPSE, 0.38))
    pn = out_cubic(prog(t, CAPTURE_NOTE, 0.45))
    pw = prog(t, CAPTURE_CORRECT, 0.2)

    shown_h = CAP_LH
    for i, (x, y) in enumerate(messy):
        ta = prog(t, CAPTURE_TOKEN_AT[i], 0.15)
        if ta > 0:
            shown_h = max(shown_h, y + CAP_LH * out_cubic(ta))
    text_h = lerp(shown_h, clean_h, pc)
    title_space = 84 * pn
    extra = 170 * pn
    card_h = int(CAP_PAD + title_space + text_h + 34 + extra) // 2 * 2
    card = Card(940, card_h)
    d, pad = card.draw()
    ox, oy = 50, CAP_PAD + title_space

    for i, (word, kind, _, _) in enumerate(CAPTURE_TOKENS):
        ta = prog(t, CAPTURE_TOKEN_AT[i], 0.15)
        if ta <= 0:
            continue
        mx, my = messy[i]
        w = widths[i]
        scale = lerp(0.6, 1.0, out_back(ta))
        cxw, cyw = ox + mx + w / 2, oy + my + CAP_LH / 2
        if kind == "f":
            k = fillers.index(i)
            pz = prog(t, CAPTURE_ZAPS[k], 0.24)
            if pz <= 0:
                card.add(txt(word, CAP_SIZE), cxw, cyw, 0.5, 0.5, ta, scale)
                continue
            marked = rrect(w + 14, 68, 14, (255, 222, 222, 255)).copy()
            put(marked, txt(word, CAP_SIZE, "Bold", RED), marked.width / 2, 34)
            card.add(marked, cxw, cyw, 0.5, 0.5, 1 - pz ** 1.4, 1 + 0.4 * out_cubic(pz))
            for j in range(7):
                ang = j * 2 * math.pi / 7 + k
                r = 24 + 90 * out_cubic(pz)
                card.add(circle(12 if j % 2 else 9, RED + (255,)), cxw + r * math.cos(ang), cyw + r * math.sin(ang),
                         0.5, 0.5, (1 - pz) * clamp(pz * 8))
        elif kind == "w":
            gone = prog(t, CAPTURE_COLLAPSE - 0.05, 0.15)
            card.add(txt(word, CAP_SIZE), cxw, cyw, 0.5, 0.5, ta * (1 - pw) * (1 - gone), scale)
            card.add(txt(word, CAP_SIZE, "Bold", (175, 168, 158)), cxw, cyw, 0.5, 0.5, pw * (1 - gone))
            if pw > 0 and gone < 1:
                x0 = pad + ox + mx + 2
                d.line((x0, pad + cyw + 2, x0 + (w - 8) * pw, pad + cyw + 2),
                       fill=GRAY + (int(255 * (1 - gone)),), width=5)
        else:
            nx, ny = clean[i]
            x, y = lerp(mx, nx, pc), lerp(my, ny, pc)
            px, py = ox + x + w / 2, oy + y + CAP_LH / 2
            if word == "周五前":
                flash = math.sin(math.pi * prog(t, CAPTURE_CORRECT + 0.12, 0.55))
                card.add(rrect(w + 14, 68, 14, ORANGE_SOFT + (255,)), px, py, 0.5, 0.5, flash)
                card.add(txt(word, CAP_SIZE, "Bold", ORANGE), px, py, 0.5, 0.5, flash)
                card.add(txt(word, CAP_SIZE), px, py, 0.5, 0.5, ta * (1 - flash), scale)
            else:
                card.add(txt(word, CAP_SIZE), px, py, 0.5, 0.5, ta, scale)

    working = prog(t, ZAP_START, 0.15)
    done = prog(t, CAPTURE_NOTE, 0.3)
    blink = 0.55 + 0.45 * abs(math.sin(t * 5))
    w_out, w_in = 1 - clamp(working * 2), clamp(working * 2 - 1)
    d_out, d_in = 1 - clamp(done * 2), clamp(done * 2 - 1)
    card.add(circle(18, RED + (255,)), 50, 52, 0, 0.5, blink * w_out)
    card.add(txt("正在听…", 32, "Medium", GRAY), 80, 52, 0, 0.5, w_out)
    card.add(sparkle(30, ORANGE + (255,)), 50, 52, 0, 0.5, w_in * d_out)
    card.add(txt("正在整理…", 32, "Bold", ORANGE), 92, 52, 0, 0.5, w_in * d_out)
    card.add(check_badge(34), 50, 52, 0, 0.5, d_in, lerp(0.5, 1, out_back(d_in)))
    card.add(txt("整理好了，已存成笔记", 32, "Bold", ORANGE), 96, 52, 0, 0.5, d_in)

    events = CAPTURE_ZAPS + [CAPTURE_CORRECT]
    n = sum(t >= e for e in events)
    if working > 0:
        last = max([e for e in events if t >= e], default=ZAP_START)
        bump = 1 + 0.18 * math.sin(math.pi * prog(t, last, 0.16))
        pk = prog(t, CAPTURE_COUNT, 0.25)
        card.add(label_chip(f"已清理 {n} 处", RED, (255, 232, 232)), 890, 52, 1, 0.5, working * (1 - pk), bump)
        card.add(label_chip(f"{n_messy} 字 → {n_clean} 字", ORANGE, ORANGE_SOFT), 890, 52, 1, 0.5, pk,
                 lerp(0.6, 1, out_back(pk)))

    if pn > 0:
        card.add(txt("和 Allen 的会前准备", 48, "Black"), 50, oy - 50, 0, 0.5, clamp((pn - 0.45) / 0.55))
        ty = oy + text_h + 40
        for j, tag in enumerate(["#会议", "#Allen"]):
            pt = out_back(prog(t, CAPTURE_NOTE + 0.1 + j * 0.1, 0.35))
            if pt > 0:
                card.add(label_chip(tag, ORANGE, ORANGE_SOFT), 50 + j * 140 + 60 * (1 - pt), ty, 0, 0.5, clamp(pt))
        pt = prog(t, CAPTURE_NOTE + 0.3, 0.3)
        if pt > 0:
            card.add(rrect(40, 40, 10, WHITE + (255,), ORANGE + (255,), 4), 50, ty + 80, 0, 0.5, pt)
            card.add(txt("周五前把报价发给 Allen", 34, "Medium"), 108, ty + 80, 0, 0.5, pt)

    shake = 0.0
    if t > CAPTURE_COLLAPSE + 0.3:
        u = t - CAPTURE_COLLAPSE - 0.3
        shake = 10 * math.sin(u * 75) * math.exp(-u * 10)
    bump = 1 + 0.03 * math.sin(math.pi * prog(t, CAPTURE_NOTE, 0.3))
    put(layer, card.img, 540 + shake, CAP_TOP - card.pad + cdy, cs * bump, ca, ay=0)


# ---------- the note wall ----------

WALL_COLS, WALL_ROWS = 25, 40
CELL_W, CELL_H, CELL_GAP = 120, 80, 12
WALL_W = WALL_COLS * (CELL_W + CELL_GAP) + CELL_GAP
WALL_H = WALL_ROWS * (CELL_H + CELL_GAP) + CELL_GAP
VIEW_TOP, VIEW_W, VIEW_H = 690, 1080, 1010
VIEW_CX, VIEW_CY = 540, VIEW_TOP + VIEW_H / 2
WALL_SCALE_FROM, WALL_SCALE_TO = 1.6, 0.31

WALL_TITLES = [
    "去东京上野公园看樱花", "R-1 项目设计调研", "海外零售销售计划", "今天和客户聊了一小时",
    "为什么优秀产品不断做减法", "AI 笔记的新方向", "这次旅行拍了很多照片", "最近发现专注力下降",
    "复盘：三个以后必须坚持", "记录是为了不断思考", "周会纪要", "读书笔记：思考快与慢",
    "新品定价的几种思路", "用户访谈 #12", "健身计划第 3 周", "竞品分析：输入法",
    "周末菜单", "年度目标拆解", "团队分工调整", "灵感：语音转待办",
    "播客摘录", "季度 OKR 草稿", "设计评审要点", "招聘 JD 修改",
    "出差清单", "体验问题汇总", "一个关于记忆的想法", "客户反馈整理",
    "早上散步时想到的", "直播脚本初稿", "数据看板需求", "给新同事的入职指南",
]

PICKS = [
    ((5, 12), "Allen 首次会议纪要", "09/28 · 录音 42 分钟"),
    ((19, 14), "Q3 合作报价单 v2", "10/08 · 文档"),
    ((6, 27), "Allen：导出太慢了", "10/10 · 闪念"),
    ((18, 26), "和 Allen 的会前准备", "今天 · 刚刚记下"),
]


def cell_center(c, r):
    return (CELL_GAP + c * (CELL_W + CELL_GAP) + CELL_W / 2, CELL_GAP + r * (CELL_H + CELL_GAP) + CELL_H / 2)


@lru_cache(1)
def walls():
    import random

    rnd = random.Random(3)
    wall = Image.new("RGBA", (WALL_W, WALL_H), (0, 0, 0, 0))
    cell = rrect(CELL_W, CELL_H, 10, WHITE + (255,), LINE + (255,), 1)
    d = ImageDraw.Draw(wall)
    ft, fs = font("Bold", 13), font("Regular", 10)
    pastel = [(255, 214, 196), (214, 226, 240), (222, 236, 214), (240, 226, 206), (232, 220, 240)]
    for r in range(WALL_ROWS):
        for c in range(WALL_COLS):
            x, y = CELL_GAP + c * (CELL_W + CELL_GAP), CELL_GAP + r * (CELL_H + CELL_GAP)
            wall.alpha_composite(cell, (x, y))
            d.text((x + 10, y + 9), rnd.choice(WALL_TITLES)[:8], font=ft, fill=INK + (255,))
            has_img = rnd.random() < 0.22
            for k in range(2):
                bw = rnd.randint(40, 62 if has_img else 96)
                d.rounded_rectangle((x + 10, y + 34 + k * 13, x + 10 + bw, y + 40 + k * 13), 3, fill=(228, 223, 215, 255))
            if has_img:
                d.rounded_rectangle((x + 78, y + 32, x + 110, y + 60), 5, fill=rnd.choice(pastel) + (255,))
            d.text((x + 10, y + 62), f"{rnd.randint(1, 12):02d}/{rnd.randint(1, 28):02d}", font=fs, fill=GRAY + (255,))
    rgb = wall.convert("RGB")
    dim = Image.blend(rgb, Image.new("RGB", wall.size, PAPER), 0.72).convert("RGBA")
    dim.putalpha(wall.getchannel("A").point(lambda v: int(v * 0.8)))
    flash = Image.blend(rgb, Image.new("RGB", wall.size, ORANGE), 0.5).convert("RGBA")
    flash.putalpha(wall.getchannel("A"))
    return wall, dim, flash


@lru_cache(1)
def vignette():
    m = Image.new("L", (VIEW_W, VIEW_H), 0)
    ImageDraw.Draw(m).rounded_rectangle((90, 70, VIEW_W - 90, VIEW_H - 70), 160, fill=255)
    return m.filter(ImageFilter.GaussianBlur(70))


@lru_cache(8)
def wall_crop(which, scale):
    src = walls()[which]
    cw, ch = VIEW_W / scale, VIEW_H / scale
    box = (round(WALL_W / 2 - cw / 2), round(WALL_H / 2 - ch / 2), round(WALL_W / 2 + cw / 2), round(WALL_H / 2 + ch / 2))
    crop = src.crop(box)
    if scale >= 1:
        return crop.resize((VIEW_W, VIEW_H), Image.BICUBIC)
    return crop.resize((VIEW_W, VIEW_H), Image.LANCZOS, reducing_gap=2.0)


def wall_scale(t):
    z = in_out(prog(t, WALL_IN, WALL_ZOOM))
    s = WALL_SCALE_FROM * (WALL_SCALE_TO / WALL_SCALE_FROM) ** z
    return WALL_SCALE_TO if z >= 1 else round(s, 4)


def wall_to_screen(pt, scale):
    return VIEW_CX + (pt[0] - WALL_W / 2) * scale, VIEW_CY + (pt[1] - WALL_H / 2) * scale


def draw_wall(layer, t):
    alpha = prog(t, WALL_IN, 0.2) * (1 - prog(t, WALL_OUT, 0.35))
    if alpha <= 0:
        return
    scale = wall_scale(t)
    view = wall_crop(0, scale)
    ps = prog(t, SCAN_START, SCAN_LEN)
    if 0 < ps < 1:
        r = lerp(40, 820, out_cubic(ps))
        mask = Image.new("L", (VIEW_W, VIEW_H), 0)
        cy = VIEW_H / 2
        ImageDraw.Draw(mask).ellipse((540 - r, cy - r, 540 + r, cy + r), outline=int(255 * (1 - ps * 0.6)), width=110)
        mask = mask.filter(ImageFilter.GaussianBlur(30))
        view = Image.composite(wall_crop(2, scale), view, mask)
    dp = prog(t, WALL_FILTER, 0.25)
    if dp > 0:
        view = Image.blend(view, wall_crop(1, scale), dp) if dp < 1 else wall_crop(1, scale)
    a = ImageChops.multiply(view.getchannel("A"), vignette())
    if alpha < 1:
        a = a.point(lambda v: int(v * alpha))
    view = view.copy()
    view.putalpha(a)
    layer.alpha_composite(view, (0, VIEW_TOP))
    if 0 < ps < 1:
        r = lerp(40, 820, out_cubic(ps)) // 4 * 4
        put(layer, ring(int(r), 5, ORANGE + (255,)), VIEW_CX, VIEW_CY, 1.0, alpha * (1 - ps) * 0.9)


@lru_cache(8)
def pick_card(i):
    _, title, meta = PICKS[i]
    card = Card(455, 120, r=26, outline=ORANGE + (255,), width=3)
    badge = circle(44, ORANGE + (255,)).copy()
    put(badge, txt(str(i + 1), 26, "Black", WHITE), 22, 22)
    card.add(badge, 26, 60, 0, 0.5)
    card.add(txt(title, 30, "Bold"), 86, 44, 0, 0.5)
    card.add(txt(meta, 24, "Regular", GRAY), 86, 84, 0, 0.5)
    return card.img


SLOTS = [(298, 1262), (782, 1262), (298, 1412), (782, 1412)]


def ref_badge(n):
    b = circle(36, ORANGE_SOFT + (255,)).copy()
    put(b, txt(str(n), 22, "Black", ORANGE), 18, 18)
    return b


def scene_meeting(layer, t):
    t0 = M0
    header(layer, t, t0, "01", "会议", (("开会前，", INK), ("帮你备好功课", ORANGE)), MEETING_ASK, SCAN_START)

    a, s, dy = appear(t, MEETING_ASK)
    if a > 0:
        label = "下午和 Allen 有个会，帮我准备一下"
        w = int(text_width(label, 42)) + 140
        bubble = with_shadow(rrect(w, 112, 56, ORANGE + (255,)), color=(200, 60, 0), opacity=0.3)
        img, pad = bubble[0].copy(), bubble[1]
        put(img, mic_icon(44, WHITE), pad + 58, pad + 56)
        put(img, txt(label, 42, "Bold", WHITE), pad + 92, pad + 56, ax=0)
        put(layer, img, 540, 616 + dy, s, a)

    draw_wall(layer, t)

    pa, ps_, pdy = appear(t, SCAN_START - 0.15, rise=30)
    pill_alpha = pa * (1 - prog(t, WALL_OUT, 0.25))
    if pill_alpha > 0:
        found = prog(t, WALL_FILTER, 0.2)
        n = int(1000 * out_cubic(prog(t, SCAN_START - 0.05, SCAN_LEN)))
        w = 640
        base, pad = card_base(w, 104, 52, WHITE, None, 0, (70, 45, 20), 0.22)
        img = base.copy()
        put(img, rich((("翻阅你记下的 ", INK), (f"{n:,}", ORANGE), (" 条笔记", INK)), 40, "Black"),
            pad + w / 2, pad + 52, alpha=1 - found)
        put(img, check_badge(44), pad + 120, pad + 52, alpha=found)
        put(img, rich((("找到 ", INK), ("4", ORANGE), (" 条相关记忆", INK)), 40, "Black"), pad + 160, pad + 52,
            ax=0, alpha=found)
        bump = 1 + 0.06 * math.sin(math.pi * found)
        put(layer, img, VIEW_CX, VIEW_CY + pdy, ps_ * bump, pill_alpha)

    scale_now = wall_scale(t)
    for i, (cell, _, _) in enumerate(PICKS):
        pp = prog(t, WALL_PICKS[i], 0.35)
        if pp <= 0:
            continue
        sx, sy = wall_to_screen(cell_center(*cell), scale_now)
        pf = in_out(prog(t, WALL_FLY + i * 0.06, 0.45))
        tx, ty = SLOTS[i]
        x, y = lerp(sx, tx, pf), lerp(sy, ty, pf)
        sc = lerp(lerp(CELL_W * WALL_SCALE_TO / 455, 0.62, out_back(pp)), 1.0, pf)
        if pf < 1:
            put(layer, glow(360, ORANGE, 0.5), x, y, sc * 1.4, clamp(pp * 3) * (1 - pf))
        put(layer, pick_card(i), x, y, sc, clamp(pp * 3))

    la = prog(t, WALL_FLY + 0.3, 0.3)
    put(layer, txt("来源：你记下的 4 条笔记", 30, "Medium", GRAY), 540, 1150, 1.0, la)

    ra, rs, rdy = appear(t, MEETING_RESULT, rise=60)
    if ra > 0:
        card = Card(940, 330, outline=ORANGE + (255,), width=3)
        card.add(sparkle(40, ORANGE + (255,)), 52, 64, 0, 0.5)
        card.add(txt("会议准备卡", 44, "Black"), 108, 64, 0, 0.5)
        card.add(txt("基于 4 条记忆", 28, "Medium", GRAY), 890, 64, 1, 0.5)
        items = [
            ("上次遗留", "数据导出功能延期", [1, 3]),
            ("本次重点", "Q3 合作排期与报价", [2]),
            ("会前要做", "周五前把报价给他", [4]),
        ]
        for i, (k, v, refs) in enumerate(items):
            ia = prog(t, MEETING_RESULT + 0.15 + i * 0.12, 0.25)
            y = 150 + i * 62
            card.add(circle(14, ORANGE + (255,)), 58, y, 0.5, 0.5, ia)
            line = rich(((k + "   ", GRAY), (v, INK)), 36, "Medium")
            card.add(line, 84, y, 0, 0.5, ia)
            for j, ref in enumerate(refs):
                rp = out_back(prog(t, MEETING_RESULT + 0.35 + i * 0.12 + j * 0.06, 0.25))
                card.add(ref_badge(ref), 84 + line.width + 14 + j * 44, y, 0, 0.5, clamp(rp), max(0.01, rp))
        put(layer, card.img, 540, 736 - card.pad + rdy, rs, ra, ay=0)


def scene_client(layer, t):
    t0 = C0
    header(layer, t, t0, "02", "客户对话", (("聊完客户，", INK), ("帮你找到机会", ORANGE)), CLIENT_CARD, CLIENT_HIGHLIGHT)

    pa = out_cubic(prog(t, t0 + 0.15, 0.6))
    put(layer, asset("mac-zh", width=680), lerp(1300, 540, pa), 763, 1.0, pa)

    ca, cs, cdy = appear(t, CLIENT_CARD, rise=70)
    if ca > 0:
        card = Card(940, 330)
        d, pad = card.draw()
        card.add(circle(18, RED + (255,)), 50, 56, 0, 0.5)
        card.add(txt("今天和客户聊了一个小时", 40, "Bold"), 82, 56, 0, 0.5)
        card.add(txt("录音 58:12 · 已转写 · 2 位发言人", 30, "Regular", GRAY), 50, 106, 0, 0.5)
        lines = [
            (("王总：", GRAY), ("你们的功能其实挺全的，", INK)),
            (("", INK), ("但我们每周要花两天时间，", INK)),
            (("", INK), ("反复整理各个渠道的数据。", INK)),
        ]
        for i, segs in enumerate(lines):
            y = 172 + i * 56
            img = rich(segs, 38, "Medium")
            x = 50 if i == 0 else 50 + text_width("王总：", 38, "Medium")
            if i >= 1:
                hp = in_out(prog(t, CLIENT_HIGHLIGHT + (i - 1) * CLIENT_HIGHLIGHT_LEN / 2, CLIENT_HIGHLIGHT_LEN / 2))
                if hp > 0:
                    x0 = pad + x - 4
                    d.rounded_rectangle(
                        (x0, pad + y - 24, x0 + (img.width + 8) * hp, pad + y + 26), 8, fill=(255, 210, 186, 255)
                    )
            card.add(img, x, y, 0, 0.5)
        put(layer, card.img, 540, 1177 + cdy, cs, ca)

    ia, is_, idy = appear(t, CLIENT_INSIGHT, rise=80, from_scale=0.6)
    if ia > 0:
        card = Card(940, 300, fill=ORANGE + (255,), shadow=(200, 60, 0), opacity=0.35)
        card.add(sparkle(40, WHITE + (255,)), 52, 58, 0, 0.5)
        card.add(txt("发现机会", 40, "Bold", WHITE), 106, 58, 0, 0.5)
        card.add(txt("真正的痛点不是功能少，", 46, "Black", WHITE), 50, 130, 0, 0.5)
        card.add(txt("而是反复整理数据。", 46, "Black", WHITE), 50, 192, 0, 0.5)
        fa = prog(t, CLIENT_INSIGHT + 0.35, 0.3)
        card.add(txt("下一步：带一份「自动周报」方案去跟进", 32, "Medium", (255, 226, 210)), 50, 254, 0, 0.5, fa)
        put(layer, card.img, 540, 1540 + idy, is_, ia)


TODO_TEXT = "周五前把报价发给王总，下周一约个设计评审，对了，记得回 Allen 的邮件"
TODOS = [("把报价发给王总", "周五"), ("约设计评审", "下周一 10:00"), ("回复 Allen 的邮件", "今天")]


def scene_todo(layer, t):
    t0 = T0
    header(layer, t, t0, "03", "待办", (("随口一说，", INK), ("变成待办", ORANGE)), TODO_SPEAK, TODO_SPLIT)

    wa, ws, wdy = appear(t, t0 + 0.15, rise=80)
    if wa > 0:
        for k in range(2):
            phase = ((t - t0) / 1.4 + k / 2) % 1.0
            r = int(lerp(100, 260, phase)) // 4 * 4
            put(layer, ring(r, 3, ORANGE + (255,)), 537, 763 + wdy, 1.0, wa * 0.5 * (1 - phase) ** 1.5)
        put(layer, asset_shadowed("watch-zh", 400), 540, 760 + wdy, ws, wa)

    split = prog(t, TODO_SPLIT - 0.05, 0.25)
    ba, bs, bdy = appear(t, TODO_SPEAK - 0.3, rise=60)
    if ba > 0 and split < 1:
        card = Card(940, 250, fill=INK + (255,), opacity=0.25)
        d, pad = card.draw()
        for k in range(16):
            amp = 0.3 + 0.7 * abs(math.sin(t * 9 + k * 0.9) * math.sin(t * 4.3 + k * 1.7))
            if t > TODO_SPEAK + TODO_SPEAK_LEN:
                amp *= 0.25
            h = 6 + 30 * amp
            x = pad + 50 + k * 13
            d.rounded_rectangle((x, pad + 56 - h / 2, x + 6, pad + 56 + h / 2), 3, fill=(255, 140, 90, 255))
        card.add(txt("在手表上说了一句", 30, "Medium", (190, 186, 180)), 270, 56, 0, 0.5)
        lines = wrap(TODO_TEXT, 42, 840, "Medium")
        n = int(len(TODO_TEXT) * prog(t, TODO_SPEAK, TODO_SPEAK_LEN))
        for i, line in enumerate(lines):
            shown = line[: max(0, n)]
            n -= len(line)
            if shown:
                card.add(txt(shown, 42, "Medium", WHITE), 50, 132 + i * 64, 0, 0.5)
        put(layer, card.img, 540, 1133 + bdy, bs * (1 - 0.15 * split), ba * (1 - split))

    arrived = 0
    for i, (title, due) in enumerate(TODOS):
        ti = TODO_SPLIT + i * TODO_STEP
        p = prog(t, ti, 0.45)
        if p <= 0:
            continue
        arrived += t >= ti + 0.2
        card = Card(940, 128, r=32)
        card.add(rrect(46, 46, 12, WHITE + (255,), ORANGE + (255,), 4), 50, 64, 0, 0.5)
        card.add(txt(title, 42, "Bold"), 122, 64, 0, 0.5)
        dw = int(text_width(due, 32)) + 40
        chip = rrect(dw, 56, 28, ORANGE_SOFT + (255,)).copy()
        put(chip, txt(due, 32, "Bold", ORANGE), dw / 2, 28)
        card.add(chip, 890, 64, 1, 0.5)
        y = lerp(1133, 1074 + i * 156, out_cubic(p))
        put(layer, card.img, 540, y, lerp(0.5, 1, out_back(p)), clamp(p * 2))

    sa, ss, sdy = appear(t, TODO_SPLIT + 0.1, rise=30)
    if sa > 0:
        done = prog(t, TODO_SUMMARY, 0.25)
        label = f"已创建 {max(1, arrived)} 项待办"
        w = int(text_width(label, 38)) + 72
        pill = rrect(w, 88, 44, WHITE + (255,), LINE + (255,), 2).copy()
        put(pill, txt(label, 38, "Bold", GRAY), w / 2, 44)
        put(layer, pill, 540, 1538 + sdy, ss, sa * (1 - done))
        final = "3 项待办已创建，到点提醒你"
        w = int(text_width(final, 38)) + 140
        pill = rrect(w, 88, 44, ORANGE + (255,)).copy()
        put(pill, check_badge(44, WHITE, ORANGE), 58, 44)
        put(pill, txt(final, 38, "Bold", WHITE), 96, 44, ax=0)
        bump = 1 + 0.08 * math.sin(math.pi * done)
        put(layer, pill, 540, 1538 + sdy, ss * bump, sa * done)


def scene_outro(layer, t):
    ly = 650
    p = prog(t, OUTRO_LOGO, 0.6)
    if p > 0:
        put(layer, glow(900, ORANGE, 0.35), 540, ly, lerp(0.5, 1.0, out_cubic(p)), out_cubic(p))
        put(layer, asset("logo", height=300), 540, ly, out_back(p, 1.6), clamp(p * 2.5), rotate=lerp(-40, 0, out_cubic(p)))
        for k in range(8):
            ang = k * math.pi / 4 + 0.3
            bp = prog(t, OUTRO_LOGO + 0.1, 0.8)
            r = lerp(150, 330, out_cubic(bp))
            put(layer, sparkle(34 if k % 2 else 24, ORANGE + (255,)), 540 + r * math.cos(ang), ly + r * math.sin(ang),
                1.0, (1 - bp) * clamp(bp * 6))

    a, s, dy = appear(t, OUTRO_WORD)
    put(layer, txt("闪念贝壳", 132, "Black"), 540, 960 + dy, s, a)
    a, s, dy = appear(t, OUTRO_SLOGAN)
    put(layer, rich((("帮你", INK), ("记", ORANGE), ("，一起", INK), ("想", ORANGE), ("。", INK)), 92, "Black"),
        540, 1165 + dy, s, a)
    a, s, dy = appear(t, OUTRO_SLOGAN + 0.25)
    put(layer, txt("让每一个被记下的想法，都有下一步", 42, "Medium", GRAY), 540, 1305 + dy, s, a)


SCENE_FN = {
    "hook": scene_hook,
    "capture": scene_capture,
    "meeting": scene_meeting,
    "client": scene_client,
    "todo": scene_todo,
    "outro": scene_outro,
}

EXIT = 0.28


def render(t):
    frame = background(t)
    for name, start, end in SCENES:
        if start <= t < end or (name == SCENES[-1][0] and t >= start):
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            SCENE_FN[name](layer, t)
            p = prog(t, end - EXIT, EXIT) if name != SCENES[-1][0] else 0
            if p > 0:
                put(frame, layer, W / 2, H / 2 - 150 * in_cubic(p), 1.0, 1 - in_cubic(p))
            else:
                frame.alpha_composite(layer)
            break
    return frame.convert("RGB")


def render_index(i):
    return render(i / FPS).tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", nargs="*", type=float)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    if args.stills:
        for t in args.stills:
            path = os.path.join(OUT_DIR, f"still-{t:05.2f}.png")
            render(t).save(path)
            print(path)
        return

    total = int(DURATION * FPS)
    out = os.path.join(OUT_DIR, "video.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE,
    )
    with Pool(args.workers) as pool:
        for n, data in enumerate(pool.imap(render_index, range(total), chunksize=6)):
            ff.stdin.write(data)
            if n % 60 == 0:
                print(f"frame {n}/{total}", file=sys.stderr, flush=True)
    ff.stdin.close()
    ff.wait()
    print(out)


if __name__ == "__main__":
    main()
