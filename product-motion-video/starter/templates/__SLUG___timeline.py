"""Timing for the「__TITLE__」video (__SLUG___render.py / __SLUG___audio.py). Seconds.

Every on-screen beat and every sound effect reads its time from here, so picture and sound stay in sync.
"""

W, H = 1080, 1920
FPS = 30
DURATION = 12.0
BPM = 100

HOOK = "想法很多，记下的很少"
HOOK_AT, HOOK_CPS = 0.3, 0.09
HOOK_OUT = 2.0

POINTS = [("记", "随口一说，自动成稿"), ("想", "翻出相关的旧笔记"), ("做", "拆成带时间的待办")]
POINT_AT = [2.3, 3.0, 3.7]
POINTS_OUT = 7.2

LOGO = 7.6
TITLE_AT = LOGO + 0.3
SLOGAN_AT = TITLE_AT + 0.45
STORE_AT = SLOGAN_AT + 0.6


def hook_times():
    return [HOOK_AT + i * HOOK_CPS for i in range(len(HOOK))]


def sfx_events():
    ev = [(t, "tick") for t in hook_times()]
    ev += [(HOOK_OUT, "swipe")]
    ev += [(t, "pop") for t in POINT_AT]
    ev += [(POINTS_OUT, "whoosh"), (LOGO, "logo"), (TITLE_AT, "pop_hi"), (SLOGAN_AT, "check")]
    return sorted(ev)
