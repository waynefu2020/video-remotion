"""Render the 32s ideaShell memory video.

    python3 memory_render.py                  # -> out/memory-video.mp4 (no audio)
    python3 memory_render.py --stills 2.4 8   # PNG stills -> out/m-still-*.png
"""

import argparse
import math
import os
import random
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import render as R
from render import (Card, appear, asset, check_badge, check_icon, circle, clamp, font, glow, in_cubic, in_out,
                    label_chip, lerp, mic_icon, out_back, out_cubic, prog, put, ref_badge, rich, ring, rrect,
                    sparkle, text_width, txt)
from timeline import GRAY, INK, LINE, ORANGE, ORANGE_SOFT, PAPER, RED, WHITE
from memory_timeline import *  # noqa: F403

OUT_DIR = R.OUT_DIR
FOCAL = 900.0
CX, CY = 540, 960
EXIT = 0.28


def blit(dst, img, x, y):
    x, y = int(round(x - img.width / 2)), int(round(y - img.height / 2))
    if x >= dst.width or y >= dst.height or x + img.width <= 0 or y + img.height <= 0:
        return
    if x < 0 or y < 0 or x + img.width > dst.width or y + img.height > dst.height:
        sx, sy = max(0, -x), max(0, -y)
        img = img.crop((sx, sy, min(img.width, dst.width - x), min(img.height, dst.height - y)))
        x, y = x + sx, y + sy
    dst.alpha_composite(img, (x, y))


def fade(img, a):
    return R.with_alpha(img, clamp(a))


def shake_at(t, starts, amp=12, decay=11):
    s = 0.0
    for t0 in starts:
        if t > t0:
            u = t - t0
            s += amp * math.sin(u * 80) * math.exp(-u * decay)
    return s


@lru_cache(16)
def bubble(text):
    w = int(text_width(text, 42)) + 140
    img, pad = with_shadow_cached(w)
    img = img.copy()
    put(img, mic_icon(44, WHITE), pad + 58, pad + 56)
    put(img, txt(text, 42, "Bold", WHITE), pad + 92, pad + 56, ax=0)
    return img


@lru_cache(16)
def with_shadow_cached(w):
    return R.with_shadow(rrect(w, 112, 56, ORANGE + (255,)), color=(200, 60, 0), opacity=0.3)


def draw_bubble(layer, t, text, t_in, t_out=None, y=300):
    a, s, dy = appear(t, t_in)
    if t_out is not None:
        o = prog(t, t_out, 0.22)
        a *= 1 - o
        dy -= 60 * out_cubic(o)
    put(layer, bubble(text), 540, y + dy, s, a)


def chapter(layer, t, t0, num, line1, line2):
    out = prog(t, t0 + 0.72, 0.22)
    a, s, dy = appear(t, t0 + 0.02, rise=90)
    put(layer, txt(num, 260, "Black", ORANGE), 540, 700 + dy - 80 * out, s, a * (1 - out))
    a, s, dy = appear(t, t0 + 0.12)
    put(layer, txt(line1, 84, "Black"), 540, 925 + dy - 80 * out, s, a * (1 - out))
    a, s, dy = appear(t, t0 + 0.2)
    put(layer, line2 if isinstance(line2, Image.Image) else txt(line2, 84, "Black"), 540, 1040 + dy - 80 * out, s,
        a * (1 - out))


# ====================== hook: memory tunnel ======================

N_T = 440
T_Z = 600 + np.arange(N_T) * 25.0
T_TH = np.arange(N_T) * 2.39996
T_R = 780 + 160 * np.sin(np.arange(N_T) * 1.7)
T_V = np.arange(N_T) % 8
CARD_WW = 290
PASTEL = [(255, 214, 196), (214, 226, 240), (222, 236, 214), (240, 226, 206), (232, 220, 240)]


@lru_cache(8)
def mini_card(v):
    rnd = random.Random(v * 7 + 1)
    w, h = 320, 210
    img = rrect(w, h, 24, WHITE + (255,), LINE + (255,), 2).copy()
    d = ImageDraw.Draw(img)
    put(img, txt(R.WALL_TITLES[(v * 5) % len(R.WALL_TITLES)][:9], 30, "Bold"), 24, 44, ax=0)
    has_img = v % 3 == 0
    for k in range(3):
        bw = rnd.randint(110, 170 if has_img else 260)
        d.rounded_rectangle((24, 84 + k * 30, 24 + bw, 98 + k * 30), 7, fill=(228, 223, 215, 255))
    if has_img:
        d.rounded_rectangle((214, 80, 296, 160), 14, fill=PASTEL[v % 5] + (255,))
    if v % 4 == 1:
        d.ellipse((276, 26, 296, 46), fill=ORANGE + (255,))
    put(img, txt(f"{rnd.randint(1, 12):02d}/{rnd.randint(1, 28):02d}", 22, "Regular", GRAY), 24, 182, ax=0)
    return img


def quant_w(w):
    step = 2 if w < 60 else 4 if w < 200 else 10
    return max(4, int(w // step * step))


@lru_cache(1600)
def mini_scaled(v, w):
    base = mini_card(v)
    return base.resize((w, max(2, round(w * base.height / base.width))), Image.LANCZOS, reducing_gap=2.0)


@lru_cache(2400)
def wall_card(v, w, deg):
    img = mini_scaled(v, w)
    img = img.resize((img.width, max(2, int(img.height * 0.78))), Image.BICUBIC)
    return img.rotate(deg, Image.BICUBIC, expand=True) if deg % 360 else img


def wall_deg(th, amount=1.0):
    d = (90 - math.degrees(th)) % 360
    if d > 180:
        d -= 360
    return int(round(d * amount / 4)) * 4


def cam_z(t):
    return 9200 * prog(t, FLIGHT_START, FLIGHT_END - FLIGHT_START) ** 2.3


def tunnel_proj(t):
    zr = T_Z - cam_z(t)
    th = T_TH + 1.2 * prog(t, FLIGHT_START, FLIGHT_END - FLIGHT_START) ** 2
    zs = np.maximum(zr, 1.0)
    return CX + FOCAL * T_R * np.cos(th) / zs, CY + FOCAL * T_R * np.sin(th) / zs, CARD_WW * FOCAL / zs, zr, th


RIB_Z = 600 + np.arange(24) * 480.0
RIB_R = 1000


Q_LINES = ["去年王总说的预算，", "是多少来着？"]
Q_SIZE, Q_YS = 96, (850, 985)


@lru_cache(1)
def question_layer():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for line, y in zip(Q_LINES, Q_YS):
        put(img, txt(line, Q_SIZE, "Black"), 540, y)
    return img


@lru_cache(1)
def particles():
    a = np.array(question_layer().getchannel("A"))
    ys, xs = np.nonzero(a[::5, ::5] > 150)
    xs, ys = xs * 5.0, ys * 5.0
    rnd = np.random.default_rng(5)
    n = N_T + 520
    idx = rnd.permutation(len(xs))
    idx = np.resize(idx, n)
    px, py = xs[idx] + rnd.uniform(-2, 2, n), ys[idx] + rnd.uniform(-2, 2, n)
    ang = np.arctan2(py - 920, px - 540) + rnd.normal(0, 0.5, n)
    sp = rnd.uniform(60, 460, n)
    orange = rnd.random(n) < 0.28
    return px, py, np.cos(ang) * sp, np.sin(ang) * sp, orange


def draw_typing(layer, t):
    n = int(sum(len(s) for s in Q_LINES) * prog(t, TYPE_START, TYPE_END - TYPE_START))
    cursor = None
    for line, y in zip(Q_LINES, Q_YS):
        left = 540 - text_width(line, Q_SIZE, "Black") / 2
        shown = line[: max(0, n)]
        if shown:
            img = txt(shown, Q_SIZE, "Black")
            put(layer, img, left, y, ax=0)
            cursor = (left + img.width, y)
        elif cursor is None:
            cursor = (left, y)
        n -= len(line)
    typing = TYPE_START <= t <= TYPE_END
    if typing or int(t * 3.2) % 2 == 0:
        x, y = cursor
        ImageDraw.Draw(layer).rounded_rectangle((x + 6, y - 56, x + 16, y + 50), 4, fill=ORANGE + (255,))


def fog(zr):
    return clamp((4800 - zr) / 2800) ** 1.6


def draw_tunnel(layer, t, alpha=1.0):
    x, y, w, zr, th = tunnel_proj(t)
    px, py, _, _, _ = tunnel_proj(t - 1 / FPS)
    speed = clamp((cam_z(t) - cam_z(t - 1 / FPS)) / 520)
    order = np.argsort(-zr)
    streaks = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(streaks)
    for rz in RIB_Z - cam_z(t):
        if rz < 120:
            continue
        r = FOCAL * RIB_R / rz
        ra = alpha * fog(rz) * 0.55
        if ra > 0.02 and r < 1600:
            sd.ellipse((CX - r, CY - r, CX + r, CY + r), outline=(200, 190, 178, int(255 * ra)),
                       width=max(1, int(r / 110)))
    for i in order:
        if zr[i] < 140 or w[i] < 5 or w[i] > 1100:
            continue
        a = alpha * fog(zr[i])
        if speed > 0.05 and w[i] > 30:
            col = (ORANGE if T_V[i] % 4 == 1 else (190, 180, 168)) + (int(150 * speed * a),)
            sd.line((px[i], py[i], x[i], y[i]), fill=col, width=max(2, int(w[i] / 40)))
    layer.alpha_composite(streaks)
    glow_done = False
    for i in order:
        if not glow_done and zr[i] < 2600:
            put(layer, glow(1000, ORANGE, 0.6), CX, CY, 1.0, alpha * (0.6 + 0.4 * prog(t, FLIGHT_START, 1.0)))
            glow_done = True
        if zr[i] < 140 or w[i] < 5 or w[i] > 1100:
            continue
        a = alpha * fog(zr[i])
        if a <= 0.02:
            continue
        img = wall_card(int(T_V[i]), quant_w(w[i]), wall_deg(th[i]))
        blit(layer, img if a > 0.98 else fade(img, a), x[i], y[i])


@lru_cache(1)
def frozen_tunnel():
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_tunnel(layer, FLIGHT_END)
    return layer.filter(ImageFilter.GaussianBlur(7))


def draw_particles(layer, t):
    px, py, vx, vy, orange = particles()
    ue = out_cubic(prog(t, SHATTER, 0.45))
    ex, ey = px + vx * ue, py + vy * ue
    m = in_out(prog(t, MORPH_START, MORPH_END - MORPH_START))
    tx, ty, tw, _, tth = tunnel_proj(FLIGHT_START)
    spark_a = 1 - prog(t, SHATTER + 0.1, 0.55)
    for i in range(N_T, len(px)):
        if spark_a > 0:
            col = (ORANGE if orange[i] else INK) + (int(255 * spark_a),)
            blit(layer, circle(6, col), ex[i], ey[i])
    for i in range(N_T):
        x, y = lerp(ex[i], tx[i], m), lerp(ey[i], ty[i], m)
        if m < 0.4:
            col = (ORANGE if orange[i] else INK) + (int(255 * (1 - m / 0.4 * 0.5)),)
            blit(layer, circle(8, col), x, y)
        if m > 0.15:
            ww = lerp(10, tw[i], m)
            fa = clamp((m - 0.15) / 0.5) * fog(T_Z[i])
            if 5 <= ww <= 1100 and fa > 0.02:
                blit(layer, fade(wall_card(int(T_V[i]), quant_w(ww), wall_deg(tth[i], m)), fa), x, y)


def month_label(k):
    total = 2026 * 12 + 9 - k
    return f"{total // 12}.{total % 12 + 1:02d}"


def draw_month_counter(layer, t):
    a = prog(t, FLIGHT_START - 0.1, 0.15) * (1 - prog(t, FLIGHT_END + 0.25, 0.2))
    if a <= 0:
        return
    p = prog(t, FLIGHT_START, FLIGHT_END - FLIGHT_START)
    k = sum(p >= ((j + 1) / (MONTHS + 1)) ** 0.6 for j in range(MONTHS))
    if t >= FLIGHT_END:
        k = MONTHS
    base, pad = R.card_base(420, 116, 58, WHITE, None, 0, (70, 45, 20), 0.22)
    img = base.copy()
    d = ImageDraw.Draw(img)
    x0, y0 = pad + 66, pad + 58
    for off in (0, 26):
        d.polygon([(x0 + off, y0 - 18), (x0 + off, y0 + 18), (x0 + off - 26, y0)], fill=ORANGE + (255,))
    put(img, txt(month_label(k), 60, "Black"), pad + 250, y0)
    tick = prog(t, max([FLIGHT_START + (FLIGHT_END - FLIGHT_START) * ((j + 1) / (MONTHS + 1)) ** 0.6
                         for j in range(k)] or [0]), 0.1)
    put(layer, img, 540, 300, 1 + 0.06 * math.sin(math.pi * tick), a)


def found_card(t):
    card = Card(920, 310, r=40)
    d, pad = card.draw()
    card.add(circle(18, RED + (255,)), 46, 56, 0, 0.5)
    card.add(txt("客户会议录音 · 2025.11.12 · 第 23 分钟", 30, "Medium", GRAY), 78, 56, 0, 0.5)
    lead = "王总："
    lw = text_width(lead, 50, "Medium")
    pre = "预算控制在 "
    pw = text_width(pre, 54, "Black")
    key = "80 万"
    kw = text_width(key, 54, "Black")
    y = 150
    hp = in_out(prog(t, FOUND_MARK, 0.28))
    if hp > 0:
        x0 = pad + 46 + lw + pw - 6
        d.rounded_rectangle((x0, pad + y - 34, x0 + (kw + 14) * hp, pad + y + 36), 10, fill=(255, 205, 178, 255))
    card.add(txt(lead, 50, "Medium", GRAY), 46, y, 0, 0.5)
    card.add(rich(((pre, INK), (key, ORANGE if hp > 0.5 else INK), (" 以内", INK)), 54, "Black"), 46 + lw, y, 0, 0.5)
    for k in range(40):
        amp = 0.25 + 0.75 * abs(math.sin(k * 0.9) * math.sin(k * 0.37 + 1))
        hh = 6 + 34 * amp
        x = pad + 46 + k * 21
        col = ORANGE if k < 17 else (225, 220, 212)
        d.rounded_rectangle((x, pad + 250 - hh / 2, x + 9, pad + 250 + hh / 2), 4, fill=col + (255,))
    return card.img


def scene_hook(layer, t):
    if t < SHATTER:
        draw_typing(layer, t)
    flash = 1 - prog(t, SHATTER, 0.25)
    if SHATTER <= t < SHATTER + 0.25:
        put(layer, glow(1400, ORANGE, 0.5), 540, 920, 1.0, flash)
    if SHATTER <= t < FLIGHT_START:
        draw_particles(layer, t)
    if FLIGHT_START <= t < FLIGHT_END:
        draw_tunnel(layer, t)
    if t >= FLIGHT_END:
        dim = lerp(1.0, 0.22, prog(t, FLIGHT_END, 0.12)) * (1 - prog(t, 4.0, 0.4))
        put(layer, frozen_tunnel(), 540, 960, 1.0, dim)
    draw_month_counter(layer, t)

    if t >= FOUND_FLY:
        p = out_cubic(prog(t, FOUND_FLY, FOUND_LAND - FOUND_FLY))
        z = lerp(7000, FOCAL, p)
        sh = shake_at(t, [FOUND_LAND, SLAM_1, SLAM_2], 10)
        land = prog(t, FOUND_LAND, 0.35)
        if land > 0:
            put(layer, glow(1100, ORANGE, 0.45), 540, 880, lerp(0.6, 1.1, out_cubic(land)), 1 - land)
            put(layer, ring(int(lerp(200, 620, out_cubic(land))) // 4 * 4, 6, ORANGE + (255,)), 540, 880, 1.0,
                (1 - land) * 0.8)
        put(layer, found_card(t), 540 + sh, 880, FOCAL / z, clamp(p * 3))
        for k, (tt, segs, y) in enumerate([
            (SLAM_1, (("你忘了的，", INK),), 1290),
            (SLAM_2, (("它都", INK), ("记得", ORANGE), ("。", INK)), 1425),
        ]):
            q = prog(t, tt, 0.18)
            if q > 0:
                put(layer, rich(segs, 108, "Black"), 540 + sh, y, lerp(1.7, 1.0, out_cubic(q)), clamp(q * 2.5))


# ====================== memory sphere ======================

N_S = 1000
_i = np.arange(N_S) + 0.5
_phi = np.arccos(1 - 2 * _i / N_S)
_theta = math.pi * (1 + 5 ** 0.5) * _i
SP = np.stack([np.cos(_theta) * np.sin(_phi), np.cos(_phi), np.sin(_theta) * np.sin(_phi)], axis=1)
_rng = np.random.default_rng(21)
S_ORANGE = _rng.random(N_S) < 0.2
S_SCATTER = _rng.normal(0, 1, (N_S, 3))
S_SCATTER = S_SCATTER / np.linalg.norm(S_SCATTER, axis=1, keepdims=True) * _rng.uniform(2.5, 4.0, (N_S, 1))


@lru_cache(1)
def sphere_edges():
    d = ((SP[:, None, :] - SP[None, :, :]) ** 2).sum(-1)
    np.fill_diagonal(d, 9)
    nn = np.argsort(d, axis=1)[:, :2]
    return {(min(i, j), max(i, j)) for i in range(N_S) for j in nn[i]}


SR_W, SZ_C, PITCH = 520.0, 1100.0, 0.38


def yaw(t):
    y = 0.24 * t
    for q in RAPID:
        y += 2.3 * in_out(prog(t, q - 0.05, RAPID_SPIN))
    y += 5.0 * in_cubic(prog(t, OUT_FORM, 1.15))
    return y


def rotate(P, t):
    a = yaw(t)
    x = P[:, 0] * math.cos(a) + P[:, 2] * math.sin(a)
    z = -P[:, 0] * math.sin(a) + P[:, 2] * math.cos(a)
    y = P[:, 1] * math.cos(PITCH) - z * math.sin(PITCH)
    z2 = P[:, 1] * math.sin(PITCH) + z * math.cos(PITCH)
    return np.stack([x, y, z2], axis=1)


def sphere_project(t, cx, cy, scale, form=1.0):
    P = SP if form >= 1 else SP * form + S_SCATTER * (1 - form)
    Q = rotate(P, t)
    Z = SZ_C + SR_W * Q[:, 2]
    Z = np.maximum(Z, 150)
    sx = cx + scale * FOCAL * SR_W * Q[:, 0] / Z
    sy = cy + scale * FOCAL * SR_W * Q[:, 1] / Z
    return sx, sy, Z, Q


def node_at(t, direction):
    d = np.array(direction, dtype=float)
    d /= np.linalg.norm(d)
    Q = rotate(SP, t)
    return int(np.argmin(((Q - d) ** 2).sum(1)))


def draw_sphere(layer, t, cx, cy, scale, alpha=1.0, form=1.0, lit=()):
    if alpha <= 0:
        return None
    sx, sy, Z, Q = sphere_project(t, cx, cy, scale, form)
    lines = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)
    if form > 0.9:
        la = int(60 * alpha * (form - 0.9) / 0.1)
        for i, j in sphere_edges():
            if Q[i, 2] < 0.15 and Q[j, 2] < 0.15:
                ld.line((sx[i], sy[i], sx[j], sy[j]), fill=(205, 196, 184, la), width=2)
    layer.alpha_composite(lines)
    order = np.argsort(-Z)
    lit = set(lit)
    for i in order:
        if i in lit:
            continue
        dsz = int(clamp(scale * 7 * (SZ_C / Z[i]) ** 1.3, 2, 20))
        a = alpha * (0.22 + 0.78 * clamp((SZ_C + SR_W - Z[i]) / (2 * SR_W)))
        col = (255, 128, 80) if S_ORANGE[i] else (150, 140, 128)
        blit(layer, circle(dsz, col + (min(255, max(16, int(a * 16) * 16)),)), sx[i], sy[i])
    return sx, sy


def lit_node(layer, x, y, p, label=None, side=1, alpha=1.0):
    if p <= 0 or alpha <= 0:
        return
    put(layer, glow(260, ORANGE, 0.7), x, y, lerp(0.4, 1, out_cubic(p)), alpha)
    burst = prog(p, 0, 0.6)
    put(layer, ring(int(lerp(14, 70, out_cubic(burst))) // 2 * 2, 4, ORANGE + (255,)), x, y, 1.0, (1 - burst) * alpha)
    put(layer, circle(28, ORANGE + (255,)), x, y, lerp(0.3, 1, out_back(p)), alpha)
    put(layer, circle(12, WHITE + (255,)), x, y, lerp(0.3, 1, out_back(p)), alpha)
    if label:
        chip = label_chip(label, ORANGE, WHITE, 32)
        chip = R.with_shadow(chip, blur=12, dy=6, opacity=0.18)[0]
        q = prog(p, 0.15, 0.85)
        off = 40 + chip.width / 2 - 20
        if not (24 < x + side * off - chip.width / 2 and x + side * off + chip.width / 2 < W - 24):
            side = -side
        put(layer, chip, x + side * off, y, lerp(0.6, 1, out_back(q)), clamp(q * 2) * alpha)


HOP_DIRS = [(-0.55, -0.45, -0.7), (0.6, -0.15, -0.78), (-0.4, 0.5, -0.76), (0.5, 0.45, -0.74)]
HOP_LABELS = ["王总", "预算 80 万", "付款条款", "嫌交付慢"]

RAPID_QA = [
    ("去年读的那本书讲了什么？", "《思考，快与慢》：直觉快，推理慢", "3 条读书笔记 · 2025.08"),
    ("上次体检医生让我注意啥？", "少熬夜，3 个月后复查血脂", "体检录音 · 2026.06"),
    ("小林生日是哪天？", "11 月 26 日", "闲聊时提到 · 2025.04"),
]


@lru_cache(8)
def hop_nodes():
    return [node_at(HOPS[k], HOP_DIRS[k]) for k in range(4)]


@lru_cache(8)
def rapid_node(k):
    return node_at(RAPID[k] + 0.5, (0.12, -0.1, -1))


def sphere_frame(t):
    """Where the sphere sits during the recall scene: (cx, cy, scale)."""
    shrink = in_out(prog(t, SHRINK, 0.5))
    back = in_out(prog(t, RAPID[0] - 0.3, 0.4))
    cy = lerp(lerp(990, 600, shrink), 960, back)
    sc = lerp(lerp(1.0, 0.55, shrink), 1.0, back)
    return 540, cy, sc


def icon_circle(kind):
    d = 58
    img = circle(d, (236, 234, 231, 255)).copy()
    dr = ImageDraw.Draw(img)
    c = d / 2
    if kind == "glasses":
        for ox in (-10, 10):
            dr.ellipse((c + ox - 7, c - 6, c + ox + 7, c + 8), outline=INK + (255,), width=3)
        dr.line((c - 3, c, c + 3, c), fill=INK + (255,), width=3)
    elif kind == "check":
        img.alpha_composite(check_icon(34, INK + (255,), 4), (12, 13))
    return img


def recall_card(t):
    card = Card(800, 372, r=44)
    d, pad = card.draw()
    card.add(sparkle(34, ORANGE + (255,)), 40, 54, 0, 0.5)
    card.add(sparkle(16, ORANGE + (255,)), 64, 38, 0, 0.5)
    card.add(txt("回忆与行动", 34, "Bold"), 92, 54, 0, 0.5)
    d.line((pad + 36, pad + 100, pad + 764, pad + 100), fill=LINE + (255,), width=2)
    rows = [("glasses", "分析了 3 段关于“王总”的录音", True), ("glasses", "分析了 4 个记忆", True), ("check", "完成", False)]
    for i, (icon, text, chev) in enumerate(rows):
        p = prog(t, RECALL_ROWS[i], 0.25)
        if p <= 0:
            continue
        y = 156 + i * 86
        if i > 0:
            d.line((pad + 65, pad + y - 58, pad + 65, pad + y - 28), fill=(222, 219, 214, int(255 * p)), width=3)
        card.add(icon_circle(icon), 36, y, 0, 0.5, p, lerp(0.6, 1, out_back(p)))
        card.add(txt(text, 32, "Medium"), 112 + 30 * (1 - out_cubic(p)), y, 0, 0.5, p)
        if chev:
            a = int(255 * p)
            d.line((pad + 742, pad + y - 12, pad + 754, pad + y, pad + 742, pad + y + 12), fill=(170, 165, 158, a),
                   width=3)
    return card.img


def answer_card_1(t):
    card = Card(940, 300, outline=ORANGE + (255,), width=3)
    card.add(sparkle(40, ORANGE + (255,)), 50, 60, 0, 0.5)
    card.add(txt("续约前要注意", 42, "Black"), 104, 60, 0, 0.5)
    items = [("预算上限 80 万，报价别超", [1]), ("付款条款他上次有异议", [2]), ("他嫌交付慢，备好排期", [3, 4])]
    for i, (text, refs) in enumerate(items):
        ia = prog(t, ANSWER1 + 0.15 + i * 0.12, 0.25)
        y = 134 + i * 58
        card.add(circle(14, ORANGE + (255,)), 56, y, 0.5, 0.5, ia)
        line = txt(text, 36, "Medium")
        card.add(line, 82, y, 0, 0.5, ia)
        for j, ref in enumerate(refs):
            rp = out_back(prog(t, ANSWER1 + 0.3 + i * 0.12 + j * 0.06, 0.25))
            card.add(ref_badge(ref), 82 + line.width + 14 + j * 44, y, 0, 0.5, clamp(rp), max(0.01, rp))
    return card.img


@lru_cache(8)
def rapid_card(k):
    _, ans, src = RAPID_QA[k]
    card = Card(940, 196)
    card.add(sparkle(36, ORANGE + (255,)), 48, 70, 0, 0.5)
    card.add(txt(ans, 40, "Bold"), 100, 70, 0, 0.5)
    card.add(circle(12, ORANGE + (255,)), 104, 138, 0, 0.5)
    card.add(txt(src, 30, "Regular", GRAY), 126, 138, 0, 0.5)
    return card.img


def scene_recall(layer, t):
    chapter(layer, t, CH1, "01", "从 1,000 条笔记里", rich((("找到", INK), ("答案", ORANGE)), 84, "Black"))

    form = in_out(prog(t, SPHERE_FORM, 0.7))
    cx, cy, sc = sphere_frame(t)
    hops = hop_nodes()
    rap = [rapid_node(k) for k in range(3)]
    lit = [n for k, n in enumerate(hops) if t >= HOPS[k] and t < RAPID[0] - 0.3]
    lit += [n for k, n in enumerate(rap) if RAPID[k] + 0.5 <= t < (RAPID[k + 1] if k < 2 else 99)]
    sa = prog(t, SPHERE_FORM, 0.3)
    res = draw_sphere(layer, t, cx, cy, sc, sa, form, lit)
    if res is None:
        return
    sx, sy = res

    hop_alpha = 1 - prog(t, SHRINK - 0.1, 0.3)
    links = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(links)
    bp = out_cubic(prog(t, BEAM, HOPS[0] - BEAM))
    if bp > 0 and hop_alpha > 0:
        x0, y0 = 540, 362
        x1, y1 = sx[hops[0]], sy[hops[0]]
        xe, ye = lerp(x0, x1, bp), lerp(y0, y1, bp)
        ld.line((x0, y0, xe, ye), fill=ORANGE + (int(70 * hop_alpha),), width=18)
        ld.line((x0, y0, xe, ye), fill=ORANGE + (int(255 * hop_alpha),), width=5)
    for k in range(1, 4):
        lp = out_cubic(prog(t, HOPS[k] - 0.25, 0.25))
        if lp > 0 and hop_alpha > 0:
            a, b = hops[k - 1], hops[k]
            xe, ye = lerp(sx[a], sx[b], lp), lerp(sy[a], sy[b], lp)
            ld.line((sx[a], sy[a], xe, ye), fill=ORANGE + (int(70 * hop_alpha),), width=16)
            ld.line((sx[a], sy[a], xe, ye), fill=ORANGE + (int(255 * hop_alpha),), width=5)
    layer.alpha_composite(links)

    for k, n in enumerate(hops):
        p = prog(t, HOPS[k], 0.4)
        stay = 1 - prog(t, RAPID[0] - 0.35, 0.25)
        side = 1 if sx[n] < 540 else -1
        side = -side if k in (1, 3) else side
        lit_node(layer, sx[n], sy[n], p, HOP_LABELS[k] if hop_alpha > 0 else None, -1 if sx[n] < 540 else 1,
                 stay * (1 if t < SHRINK else lerp(1, 0.8, prog(t, SHRINK, 0.3))))
    for k, n in enumerate(rap):
        end = RAPID[k + 1] if k < 2 else 99
        p = prog(t, RAPID[k] + 0.5, 0.4)
        lit_node(layer, sx[n], sy[n], p, None, 1, 1 - prog(t, end - 0.05, 0.1))

    out1 = 1 - prog(t, RAPID[0] - 0.35, 0.25)
    draw_bubble(layer, t, "下周和王总谈续约，我该注意什么？", ASK1, RAPID[0] - 0.35)
    a, s, dy = appear(t, RECALL_CARD, rise=60)
    put(layer, recall_card(t), 540, 1065 + dy, s, a * out1)
    a, s, dy = appear(t, ANSWER1, rise=60)
    put(layer, answer_card_1(t), 540, 1450 + dy, s, a * out1)
    a, s, dy = appear(t, SPAN_CHIP, rise=20)
    put(layer, label_chip("跨越 11 个月 · 3 次会议 · 4 条记忆", ORANGE, ORANGE_SOFT, 30), 540, 1655 + dy, s, a * out1)

    for k, (q, _, _) in enumerate(RAPID_QA):
        nxt = RAPID[k + 1] if k < 2 else None
        draw_bubble(layer, t, q, RAPID[k], nxt)
        a, s, dy = appear(t, RAPID[k] + 0.62, rise=50)
        if nxt is not None:
            a *= 1 - prog(t, nxt, 0.2)
        put(layer, rapid_card(k), 540, 1560 + dy, s, a)


# ====================== files ======================

@lru_cache(16)
def file_icon(i, xray=False):
    label, _, color = FILES[i]
    w, h = 170, 214
    if xray:
        img = rrect(w, h, 20, ORANGE_SOFT + (255,), ORANGE + (255,), 3).copy()
    else:
        img = rrect(w, h, 20, WHITE + (255,), LINE + (255,), 2).copy()
    d = ImageDraw.Draw(img)
    d.polygon([(w - 46, 2), (w - 2, 46), (w - 46, 46)], fill=((255, 200, 175) if xray else (236, 232, 226)) + (255,))
    badge = rrect(104, 54, 14, (ORANGE if xray else color) + (255,)).copy()
    put(badge, txt(label, 30, "Black", WHITE), 52, 27)
    put(img, badge, 22, 70, ax=0)
    bar = ORANGE + (200,) if xray else (228, 223, 215, 255)
    if label == "M4A":
        for k in range(12):
            hh = 10 + 34 * abs(math.sin(k * 1.3))
            d.rounded_rectangle((24 + k * 11, 150 - hh / 2, 30 + k * 11, 150 + hh / 2), 3, fill=bar)
    else:
        for k in range(3):
            d.rounded_rectangle((24, 122 + k * 24, 24 + [120, 96, 110][k], 134 + k * 24), 6, fill=bar)
    return img


def file_slot(i):
    ang = -math.pi / 2 + i * 2 * math.pi / len(FILES)
    return ang


def draw_absorb(layer, t, alpha):
    lx, ly = 540, 985
    pulses = [ABSORB_START + i * ABSORB_STEP + 0.88 for i in range(len(FILES))]
    bump = 1 + sum(0.09 * math.sin(math.pi * prog(t, p, 0.2)) for p in pulses)
    la, ls, _ = appear(t, ABSORB_START - 0.35, rise=0, from_scale=0.5)
    put(layer, glow(700, ORANGE, 0.35 + 0.1 * (bump - 1) * 10), lx, ly, 1.0, la * alpha)
    put(layer, asset("logo", height=230), lx, ly, ls * bump, la * alpha)
    absorbed = 0
    for i, (label, name, color) in enumerate(FILES):
        t0 = ABSORB_START + i * ABSORB_STEP
        p = out_cubic(prog(t, t0, 0.35))
        if p <= 0:
            continue
        s = prog(t, t0 + 0.35, 0.22)
        dsv = prog(t, t0 + 0.6, 0.32)
        absorbed += t >= t0 + 0.88
        ang = file_slot(i)
        r = lerp(1300, 400, p)
        x, y = lx + r * math.cos(ang), ly + r * math.sin(ang) * 1.05
        icon = file_icon(i)
        if dsv < 0.25:
            img = icon.copy()
            if s > 0:
                xr = file_icon(i, True)
                cut = int(xr.height * s)
                if cut > 0:
                    img.alpha_composite(xr.crop((0, 0, xr.width, cut)), (0, 0))
                if s < 1:
                    ImageDraw.Draw(img).rectangle((0, cut - 3, img.width, cut + 3), fill=ORANGE + (255,))
            put(layer, img, x, y, 1 - 0.3 * dsv, alpha * (1 - dsv * 4))
            if s > 0 and s < 1:
                put(layer, glow(260, ORANGE, 0.5), x, y - icon.height / 2 + icon.height * s, 1.0, alpha * 0.8)
            put(layer, txt(name, 28, "Medium", GRAY), x, y + 136, 1.0, alpha * clamp(p * 2) * (1 - dsv * 4))
        if dsv > 0:
            for k in range(10):
                q = in_cubic(clamp(dsv * 1.3 - k * 0.03))
                bx = x - 60 + (k % 3) * 50
                by = y - 70 + (k // 3) * 40
                px, py = lerp(bx, lx, q), lerp(by, ly, q)
                put(layer, rrect(46, 10, 5, ORANGE + (255,)), px, py, lerp(1, 0.3, q), alpha * (1 - q ** 3))
    ca, cs, cdy = appear(t, ABSORB_START + 0.3, rise=20)
    if ca > 0:
        last = max([ABSORB_START + i * ABSORB_STEP + 0.88 for i in range(absorbed)] or [0])
        b = 1 + 0.12 * math.sin(math.pi * prog(t, last, 0.16))
        chip = label_chip(f"已读完 {absorbed} 份文件，全部变成你的记忆", ORANGE, ORANGE_SOFT, 34)
        put(layer, chip, 540, 1530 + cdy, cs * b, ca * alpha)
        put(layer, txt("PDF · Word · PPT · Excel · 图片 · 录音 · 网页链接", 32, "Medium", GRAY), 540, 1615 + cdy, cs,
            ca * alpha)


@lru_cache(8)
def page_base(v):
    rnd = random.Random(v + 40)
    w, h = 600, 800
    img = rrect(w, h, 20, WHITE + (255,), LINE + (255,), 2).copy()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((50, 60, 330, 84), 8, fill=(205, 198, 188, 255))
    for k in range(17):
        bw = rnd.randint(380, 500) if k % 6 != 5 else rnd.randint(150, 300)
        d.rounded_rectangle((50, 130 + k * 34, 50 + bw, 144 + k * 34), 6, fill=(230, 225, 217, 255))
    return img


PAGE_COUNT, TARGET_PAGE = 86, 47
CLAUSE = ["12.1 任何一方违约，应向守约方支付", "合同总额 20% 的违约金。", "12.2 因不可抗力导致无法履约的，", "双方均不承担违约责任。"]


def page_img(i, t=None):
    if i == TARGET_PAGE - 1:
        img = rrect(600, 800, 20, WHITE + (255,), LINE + (255,), 2).copy()
        d = ImageDraw.Draw(img)
        put(img, txt("第十二条  违约责任", 36, "Black"), 50, 90, ax=0)
        hp = in_out(prog(t, PAGE_MARK, 0.4)) if t is not None else 0
        for k, line in enumerate(CLAUSE):
            y = 168 + k * 50
            if k < 2 and hp > 0:
                lw = text_width(line, 28, "Medium")
                q = clamp(hp * 2 - k)
                if q > 0:
                    d.rounded_rectangle((44, y - 22, 44 + (lw + 14) * q, y + 24), 8, fill=(255, 205, 178, 255))
            put(img, txt(line, 28, "Medium", INK if k < 2 else GRAY), 50, y, ax=0)
        rnd = random.Random(9)
        for k in range(9):
            d.rounded_rectangle((50, 400 + k * 34, 50 + rnd.randint(300, 500), 414 + k * 34), 6, fill=(230, 225, 217, 255))
    else:
        img = page_base(i % 4).copy()
    put(img, txt(f"— {i + 1} —", 26, "Medium", GRAY), 300, 752)
    return img


@lru_cache(400)
def page_scaled(i, w):
    img = page_img(i)
    return img.resize((w, round(w * 4 / 3)), Image.LANCZOS, reducing_gap=2.0)


def draw_accordion(layer, t, alpha):
    draw_bubble(layer, t, "合同里的违约条款怎么写的？", ACC_ASK)
    u = prog(t, RIFFLE_START, RIFFLE_END - RIFFLE_START)
    s = (TARGET_PAGE - 1) * (1 - (1 - u) ** 3.2)
    enter = out_cubic(prog(t, ACC_START - 0.25, 0.5))
    settle = prog(t, RIFFLE_END + 0.05, 0.25)
    pages = []
    for i in range(PAGE_COUNT):
        r = i - s
        if r < -1.3 or r > 10:
            continue
        if r >= 0:
            z = 1000 + r * 170 + (1 - enter) * 1500
            x, y = 540 + r * 36, 1010 - r * 28
            a = clamp((10 - r) / 3) * (1 - settle if r > 0.5 else 1)
        else:
            z = 1000 + r * 520
            x, y = 540 + r * 560, 1010 - r * 260
            a = clamp(1 + r / 1.3) * (1 - settle)
        pages.append((z, i, x, y, a))
    for z, i, x, y, a in sorted(pages, reverse=True):
        w = int(600 * FOCAL / z * 1.0)
        if w < 20 or w > 1400 or a <= 0:
            continue
        if i == TARGET_PAGE - 1 and t >= PAGE_MARK - 0.05:
            img = page_img(i, t)
            img = img.resize((quant_w(w), round(quant_w(w) * 4 / 3)), Image.LANCZOS)
        else:
            img = page_scaled(i, quant_w(w))
        put(layer, img, x, y, 1.0, a * alpha * enter)
    n = min(PAGE_COUNT, int(s) + 1)
    found = prog(t, RIFFLE_END, 0.2)
    ca = prog(t, RIFFLE_START - 0.1, 0.2) * alpha
    if ca > 0:
        put(layer, label_chip(f"第 {n} 页", GRAY, WHITE, 32), 540, 432, 1.0, ca * (1 - found))
        put(layer, label_chip(f"第 {TARGET_PAGE} 页 / 共 {PAGE_COUNT} 页", WHITE, ORANGE, 32), 540, 432,
            lerp(0.7, 1, out_back(found)), ca * found)
    a, sc, dy = appear(t, PAGE_ANSWER, rise=50)
    if a > 0:
        card = Card(940, 196)
        card.add(sparkle(36, ORANGE + (255,)), 48, 66, 0, 0.5)
        card.add(txt("违约方需支付合同总额 20% 的违约金", 38, "Bold"), 100, 66, 0, 0.5)
        badge = rrect(66, 36, 10, FILES[0][2] + (255,)).copy()
        put(badge, txt("PDF", 20, "Black", WHITE), 33, 18)
        card.add(badge, 100, 136, 0, 0.5)
        card.add(txt("合同.pdf · 第 47 页", 30, "Regular", GRAY), 180, 136, 0, 0.5)
        put(layer, card.img, 540, 1530 + dy, sc, a * alpha)


QUOTES = [("A 公司", 3, 128000, 45, "1 年"), ("B 公司", 0, 116500, 60, "2 年"), ("C 公司", 4, 121800, 30, "1 年")]
QUOTE_FILES = [("A 公司报价", ".xlsx", 3), ("B 公司报价", ".pdf", 0), ("C 公司报价", ".jpg", 4)]
COL_X = [44, 300, 560, 790]


@lru_cache(4)
def quote_file_card(k):
    name, ext, fi = QUOTE_FILES[k]
    card = Card(300, 150, r=30)
    badge = rrect(84, 46, 12, FILES[fi][2] + (255,)).copy()
    put(badge, txt(FILES[fi][0], 24, "Black", WHITE), 42, 23)
    card.add(badge, 28, 48, 0, 0.5)
    card.add(txt(name, 32, "Bold"), 28, 100, 0, 0.5)
    card.add(txt(ext, 24, "Regular", GRAY), 128, 48, 0, 0.5)
    return card.img


def draw_compare(layer, t, alpha):
    draw_bubble(layer, t, "把三家的报价对比一下", CMP_ASK)
    xs = [196, 540, 884]
    for k in range(3):
        a, s, dy = appear(t, CMP_FILES[k])
        put(layer, quote_file_card(k), xs[k], 560 + dy, s, a * alpha)
    bp = out_cubic(prog(t, CMP_BEAMS, 0.35))
    bfade = 1 - prog(t, CMP_FILL + 1.1, 0.4)
    if bp > 0 and bfade > 0:
        beams = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(beams)
        for k in range(3):
            x0, y0 = xs[k], 640
            x1, y1 = 300 + k * 240, 860
            xe, ye = lerp(x0, x1, bp), lerp(y0, y1, bp)
            bd.line((x0, y0, xe, ye), fill=ORANGE + (int(70 * bfade * alpha),), width=16)
            bd.line((x0, y0, xe, ye), fill=ORANGE + (int(255 * bfade * alpha),), width=4)
        layer.alpha_composite(beams)
        for k in range(3):
            for j in range(3):
                q = ((t - CMP_BEAMS) * 1.6 + j / 3) % 1.0
                x, y = lerp(xs[k], 300 + k * 240, q), lerp(640, 860, q)
                put(layer, circle(14, ORANGE + (255,)), x, y, 1.0, bfade * alpha * bp)

    ta, ts, tdy = appear(t, CMP_TABLE, rise=60)
    if ta <= 0:
        return
    card = Card(960, 470, r=40)
    d, pad = card.draw()
    for j, h in enumerate(["供应商", "报价", "交付周期", "售后"]):
        card.add(txt(h, 30, "Medium", GRAY), COL_X[j], 60, 0, 0.5)
    d.line((pad + 36, pad + 104, pad + 924, pad + 104), fill=LINE + (255,), width=2)
    best = prog(t, CMP_BEST, 0.25)
    fast = prog(t, CMP_BEST + 0.18, 0.25)
    for r, (name, fi, price, days, care) in enumerate(QUOTES):
        y = 168 + r * 104
        if r:
            d.line((pad + 36, pad + y - 52, pad + 924, pad + y - 52), fill=(238, 234, 228, 255), width=2)
        ra = prog(t, CMP_FILL + r * 0.3, 0.2)
        if ra <= 0:
            continue
        card.add(circle(14, FILES[fi][2] + (255,)), COL_X[0], y, 0, 0.5, ra)
        card.add(txt(name, 36, "Bold"), COL_X[0] + 28, y, 0, 0.5, ra)
        roll = out_cubic(prog(t, CMP_FILL + r * 0.3, 0.55))
        pv = int(price * roll / 100) * 100
        price_s, days_s = f"¥{pv:,}", f"{int(days * roll)} 天"
        if r == 1 and best > 0:
            card.add(rrect(int(text_width(price_s, 36, "Bold")) + 28, 64, 14, ORANGE_SOFT + (255,)), COL_X[1] - 14,
                     y, 0, 0.5, best)
        card.add(txt(price_s, 36, "Bold", ORANGE if (r == 1 and best > 0.5) else INK), COL_X[1], y, 0, 0.5, ra)
        if r == 2 and fast > 0:
            card.add(rrect(int(text_width(days_s, 36, "Bold")) + 28, 64, 14, ORANGE_SOFT + (255,)), COL_X[2] - 14,
                     y, 0, 0.5, fast)
        card.add(txt(days_s, 36, "Bold", ORANGE if (r == 2 and fast > 0.5) else INK), COL_X[2], y, 0, 0.5, ra)
        card.add(txt(care, 36, "Bold"), COL_X[3], y, 0, 0.5, prog(t, CMP_FILL + r * 0.3 + 0.3, 0.2))
        for label, col, val, tt in (("最低价", 1, price_s, CMP_BEST), ("交付最快", 2, days_s, CMP_BEST + 0.18)):
            q = prog(t, tt, 0.3)
            if r == col and q > 0:
                chip = label_chip(label, WHITE, ORANGE, 20)
                card.add(chip, COL_X[col] + text_width(val, 36, "Bold") + 22, y - 40, 1, 0.5, clamp(q * 2),
                         lerp(0.5, 1, out_back(q)))
    put(layer, card.img, 540, 1085 + tdy, ts, ta * alpha)
    a, s, dy = appear(t, CMP_SUMMARY, rise=20)
    put(layer, label_chip("综合 3 份不同格式的文件", ORANGE, ORANGE_SOFT, 32), 540, 1385 + dy, s, a * alpha)


def scene_files(layer, t):
    chapter(layer, t, CH2, "02", "上传的文件，", rich((("都能", INK), ("问", ORANGE)), 84, "Black"))
    if t < ACC_START:
        draw_absorb(layer, t, 1 - prog(t, ACC_START - 0.25, 0.25))
    if ACC_START - 0.25 <= t < CMP_START:
        sub = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_accordion(sub, t, 1.0)
        o = prog(t, CMP_START - 0.25, 0.25)
        put(layer, sub, 540, 960 - 120 * in_cubic(o), 1.0, 1 - o)
    if t >= CMP_START:
        draw_compare(layer, t, 1.0)


# ====================== outro ======================

LOGO_Y = 700
RING_C = (540 - 8, LOGO_Y + 10)
RING_R = 74


def scene_outro(layer, t):
    form = out_cubic(prog(t, OUT_FORM, 0.45))
    col = in_out(prog(t, OUT_COLLAPSE, OUT_LOGO - OUT_COLLAPSE))
    dots_alpha = prog(t, OUT_FORM, 0.2) * (1 - prog(t, OUT_LOGO + 0.05, 0.2))
    if dots_alpha > 0:
        sx, sy, Z, Q = sphere_project(t, 540, LOGO_Y, 0.8, form)
        ang = np.arctan2(sy - LOGO_Y, sx - 540)
        tx, ty = RING_C[0] + RING_R * np.cos(ang), RING_C[1] + RING_R * np.sin(ang)
        x, y = sx + (tx - sx) * col, sy + (ty - sy) * col
        for i in np.argsort(-Z):
            dsz = int(clamp(lerp(0.8 * 7 * (SZ_C / Z[i]) ** 1.3, 6, col), 2, 18))
            a = dots_alpha * lerp(0.22 + 0.78 * clamp((SZ_C + SR_W - Z[i]) / (2 * SR_W)), 1.0, col)
            c = (255, 128, 80) if (S_ORANGE[i] or col > 0.5) else (150, 140, 128)
            blit(layer, circle(dsz, c + (min(255, max(16, int(a * 16) * 16)),)), x[i], y[i])
    p = prog(t, OUT_LOGO, 0.5)
    if p > 0:
        put(layer, glow(1000, ORANGE, 0.5), 540, LOGO_Y, lerp(0.4, 1.0, out_cubic(p)), lerp(1.0, 0.6, p))
        put(layer, asset("logo", height=300), 540, LOGO_Y, out_back(p, 1.6), clamp(p * 3))
    a, s, dy = appear(t, OUT_WORD)
    put(layer, txt("闪念贝壳", 132, "Black"), 540, 1010 + dy, s, a)
    a, s, dy = appear(t, OUT_SLOGAN)
    put(layer, rich((("帮你", INK), ("记", ORANGE), ("，一起", INK), ("想", ORANGE), ("。", INK)), 92, "Black"),
        540, 1215 + dy, s, a)
    a, s, dy = appear(t, OUT_SUB)
    put(layer, txt("让每一个被记下的想法，都有下一步", 42, "Medium", GRAY), 540, 1355 + dy, s, a)


SCENE_FN = {"hook": scene_hook, "recall": scene_recall, "files": scene_files, "outro": scene_outro}


def render(t):
    frame = R.background(t)
    for name, start, end in SCENES:
        last = name == SCENES[-1][0]
        if start <= t < end or (last and t >= start):
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            SCENE_FN[name](layer, t)
            p = prog(t, end - EXIT, EXIT) if not last else 0
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
            path = os.path.join(OUT_DIR, f"m-still-{t:05.2f}.png")
            render(t).save(path)
            print(path)
        return
    total = int(DURATION * FPS)
    out = os.path.join(OUT_DIR, "memory-video.mp4")
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE,
    )
    with Pool(args.workers) as pool:
        for n, data in enumerate(pool.imap(render_index, range(total), chunksize=4)):
            ff.stdin.write(data)
            if n % 60 == 0:
                print(f"frame {n}/{total}", file=sys.stderr, flush=True)
    ff.stdin.close()
    ff.wait()
    print(out)


if __name__ == "__main__":
    main()
