"""Timing for the 32s memory video (memory_render.py / memory_audio.py). Seconds."""

W, H = 1080, 1920
FPS = 30
DURATION = 32.0
BPM = 120

SCENES = [
    ("hook", 0.0, 4.6),
    ("recall", 4.6, 15.2),
    ("files", 15.2, 27.2),
    ("outro", 27.2, 32.0),
]

# ---- hook: question -> shatter -> memory tunnel -> found ----
TYPE_START, TYPE_END = 0.08, 0.95
SHATTER = 1.28
MORPH_START, MORPH_END = 1.55, 1.95
FLIGHT_START, FLIGHT_END = 1.95, 2.95
SILENCE_END = 3.12
FOUND_FLY = 3.12
FOUND_LAND = 3.5
FOUND_MARK = 3.62
SLAM_1, SLAM_2 = 3.92, 4.08
MONTHS = 11

# ---- recall: 1,000 notes sphere ----
CH1 = 4.6
SPHERE_FORM = 4.95
ASK1 = 5.65
BEAM = 6.1
HOPS = [6.4, 6.75, 7.1, 7.45]
SHRINK = 7.9
RECALL_CARD = 8.15
RECALL_ROWS = [8.35, 8.6, 8.85]
ANSWER1 = 9.1
SPAN_CHIP = 9.65
RAPID = [10.95, 12.35, 13.75]
RAPID_SPIN = 0.45

# ---- files ----
CH2 = 15.2
ABSORB_START = 16.05
ABSORB_STEP = 0.3
ACC_START = 19.05
ACC_ASK = 19.15
RIFFLE_START, RIFFLE_END = 19.6, 21.2
PAGE_MARK = 21.45
PAGE_ANSWER = 21.9
CMP_START = 23.05
CMP_ASK = 23.15
CMP_FILES = [23.35, 23.45, 23.55]
CMP_BEAMS = 23.8
CMP_TABLE = 23.85
CMP_FILL = 24.3
CMP_BEST = 25.4
CMP_SUMMARY = 25.85

# ---- outro ----
OUT_FORM = 27.2
OUT_COLLAPSE = 27.65
OUT_LOGO = 28.35
OUT_WORD = 28.8
OUT_SLOGAN = 29.25
OUT_SUB = 29.6

FILES = [
    ("PDF", "合同.pdf", (229, 72, 77)),
    ("DOC", "方案.docx", (47, 111, 235)),
    ("PPT", "汇报.pptx", (242, 123, 26)),
    ("XLS", "报价.xlsx", (33, 163, 102)),
    ("JPG", "白板.jpg", (142, 92, 246)),
    ("M4A", "访谈录音.m4a", (20, 184, 166)),
    ("URL", "网页链接", (100, 116, 139)),
]


def sfx_events():
    ev = []
    n_chars = 14
    for i in range(n_chars):
        ev.append((TYPE_START + (TYPE_END - TYPE_START) * i / n_chars, "type"))
    ev.append((SHATTER, "shatter"))
    ev.append((FLIGHT_START - 0.1, "tunnel"))
    for k in range(MONTHS):
        u = (k + 1) / (MONTHS + 1)
        ev.append((FLIGHT_START + (FLIGHT_END - FLIGHT_START) * u ** 0.6, "tick"))
    ev.append((FOUND_FLY, "whoosh_in"))
    ev.append((FOUND_LAND, "impact"))
    ev.append((FOUND_MARK, "marker"))
    ev.append((SLAM_1, "slam"))
    ev.append((SLAM_2, "slam"))

    ev.append((CH1, "chapter"))
    ev.append((SPHERE_FORM, "form"))
    ev.append((ASK1, "pop"))
    ev.append((BEAM, "zap"))
    ev += [(t, f"ping{i}") for i, t in enumerate(HOPS)]
    ev.append((SHRINK, "whoosh"))
    ev += [(t, "step") for t in RECALL_ROWS]
    ev.append((ANSWER1, "chime"))
    for i, t in enumerate(RAPID):
        ev.append((t - 0.05, "whip"))
        ev.append((t + 0.5, f"ping{i + 1}"))
        ev.append((t + 0.62, "pop_hi"))

    ev.append((CH2, "chapter"))
    for i in range(len(FILES)):
        t = ABSORB_START + i * ABSORB_STEP
        ev.append((t, "fly_in"))
        ev.append((t + 0.35, "scan"))
        ev.append((t + 0.6, "gulp"))
    ev.append((ACC_ASK, "pop"))
    ev.append((RIFFLE_START, "riffle"))
    ev.append((RIFFLE_END, "thud"))
    ev.append((PAGE_MARK, "marker"))
    ev.append((PAGE_ANSWER, "chime"))
    ev.append((CMP_ASK, "pop"))
    ev += [(t, "pop_hi") for t in CMP_FILES]
    ev.append((CMP_BEAMS, "zap"))
    for i in range(12):
        ev.append((CMP_FILL + i * 0.075, "tick"))
    ev.append((CMP_BEST, "chime"))

    ev.append((OUT_FORM, "form"))
    ev.append((OUT_COLLAPSE, "inhale"))
    ev.append((OUT_LOGO, "impact"))
    ev.append((OUT_SLOGAN, "sparkle"))
    return sorted(ev)
