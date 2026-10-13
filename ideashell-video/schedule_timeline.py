"""Timing for the 28s「说话乱七八糟，日程井井有条」video (schedule_render.py / schedule_audio.py). Seconds."""

import re

W, H = 1080, 1920
FPS = 30
DURATION = 28.0


def cells_of(s):
    return re.findall(r"[A-Za-z0-9]+|.", s)


def build(groups):
    """groups: [(text, kind)] with kind None (kept), "f" (口头禅) or "c" (改口)."""
    cells, marks = [], []
    for text, kind in groups:
        cs = cells_of(text)
        if kind:
            marks.append((len(cells), len(cs), kind))
        cells += cs
    removed = {i for s, n, _ in marks for i in range(s, s + n)}
    kept = [i for i in range(len(cells)) if i not in removed]
    return cells, marks, kept


# ---- round 1 ----
R1_GROUPS = [("嗯，", "f"), ("那个，", "f"), ("明早", None), ("九点，啊不是，", "c"), ("十点跟老板过方案，", None),
             ("然后那个，", "f"), ("PPT今晚得改完。", None)]
TYPE1 = (0.2, 2.45)
MARK1 = [2.75, 3.08, 3.41, 3.74]
BLOW1 = 4.25
REFLOW1 = 4.42
TASK1 = 5.55
TAGS1 = 6.2
CHECKS1 = [6.55, 6.8]
LINE1 = 7.0
OUT1 = 8.0

# ---- round 2 ----
AGAIN = 8.05
R2_GROUPS = [("就是，", "f"), ("周六我妈生日", None), ("嘛", "f"), ("，", None), ("对，", "f"), ("要订个蛋糕，", None),
             ("呃，", "f"), ("还有", None), ("那个，", "f"), ("每周二四晚上", None), ("八点，不对，", "c"),
             ("七点半去游泳，", None), ("哦对，", "f"), ("房租周日交。", None)]
TYPE2 = (8.45, 10.55)
MARK2 = [10.75 + 0.2 * k for k in range(7)]
BLOW2 = 12.3
REFLOW2 = 12.47
TASK2 = 13.4
TAGS2 = 14.05
CHECKS2 = [14.4, 14.6, 14.8, 15.0]
LINE2 = 15.2

# ---- climax: the paper grid becomes this week's calendar ----
CAL = 15.9
MORPH = 16.3
MORPH_STAGGER = 0.006
MORPH_DUR = 0.45
CAL_HEAD = 17.0
LAND = [17.25 + 0.14 * k for k in range(7)]
FLY_DUR = 0.38
SLAM = (18.6, 18.8)
CAL_OUT = 20.15

# ---- slogan row -> end card ----
SLOGAN_TEXT = "呃，就，帮你记，帮你做"
SLOGAN_DROP = 4
TYPE3 = (20.4, 20.95)
MARK3 = 21.1
BLOW3 = 21.45
REFLOW3 = 21.6
ORANGE3 = [22.15, 22.27, 22.39]
LOGO = 22.6
TITLE = 22.85
TAGLINE = 23.3
CHIPS = [23.5 + 0.08 * k for k in range(5)]
STORE = 24.05

LABELS = [
    (0.0, "mic", "你说的"),
    (2.62, "logo", "闪念贝壳整理中…"),
    (4.5, "check", "整理好了"),
    (5.45, "list", "拆成待办"),
    (6.55, "check", "已添加 2 项待办"),
    (AGAIN, "mic", "再说一段"),
    (10.65, "logo", "闪念贝壳整理中…"),
    (12.55, "check", "整理好了"),
    (13.3, "list", "拆成待办"),
    (14.4, "check", "已添加 4 项待办"),
    (CAL, "cal", "本周日程"),
    (CAL_OUT, None, ""),
]
PAGES = [(0.0, 1), (AGAIN, 2), (CAL, 3)]


def type_times(cells, span):
    t0, t1 = span
    dt = (t1 - t0) / len(cells)
    return [t0 + i * dt for i in range(len(cells))]


def sfx_events():
    ev = []
    for groups, span, marks, blow, reflow, task, tags, checks, ncards in (
        (R1_GROUPS, TYPE1, MARK1, BLOW1, REFLOW1, TASK1, TAGS1, CHECKS1, 2),
        (R2_GROUPS, TYPE2, MARK2, BLOW2, REFLOW2, TASK2, TAGS2, CHECKS2, 4),
    ):
        cells, mk, _ = build(groups)
        ev += [(t, "key") for t in type_times(cells, span)]
        ev += [(t, f"mark{k}") for k, t in enumerate(marks)]
        ev += [(blow, "blow"), (reflow, "reflow"), (task, "fly")]
        ev += [(tags + 0.12 * k, "tag") for k in range(ncards)]
        ev += [(t, "check") for t in checks]
    ev += [(LINE1, "line"), (LINE2, "line"), (AGAIN, "page")]
    ev += [(CAL, "fly"), (MORPH, "morph")]
    ev += [(CAL_HEAD + 0.04 * k, "tick") for k in range(7)]
    ev += [(t + FLY_DUR, f"land{k}") for k, t in enumerate(LAND)]
    ev += [(SLAM[0], "slam"), (SLAM[1], "slam2")]
    ev += [(CAL_OUT, "page")]
    ev += [(t, "key") for t in type_times(cells_of(SLOGAN_TEXT), TYPE3)]
    ev += [(MARK3, "mark0"), (BLOW3, "blow"), (REFLOW3, "reflow")]
    ev += [(t, f"hl{k}") for k, t in enumerate(ORANGE3)]
    ev += [(LOGO, "logo"), (TITLE, "pop")]
    ev += [(t, "tick") for t in CHIPS]
    return sorted(ev)
