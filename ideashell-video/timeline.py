"""Shared timing for picture and sound. All times are in seconds."""

W, H = 1080, 1920
FPS = 30
DURATION = 30.0
BPM = 120

ORANGE = (255, 66, 0)
ORANGE_SOFT = (255, 236, 226)
INK = (30, 30, 30)
GRAY = (122, 116, 108)
PAPER = (246, 244, 240)
LINE = (226, 220, 210)
RED = (232, 52, 52)
WHITE = (255, 255, 255)

SCENES = [
    ("hook", 0.0, 2.5),
    ("capture", 2.5, 7.5),
    ("bridge", 7.5, 8.5),
    ("meeting", 8.5, 14.0),
    ("client", 14.0, 19.5),
    ("todo", 19.5, 25.0),
    ("outro", 25.0, 30.0),
]

HOOK_LINES = [0.15, 0.85, 1.55]

CAPTURE_WORDS = ["嗯…", "那个", "下午", "和 Allen ", "的会", "……", "帮我", "准备", "一下"]
CAPTURE_FILLERS = {0, 1, 5}
CAPTURE_TYPE_START = 3.5
CAPTURE_TYPE_STEP = 0.2
CAPTURE_MARK = 5.6
CAPTURE_CLEAN = 6.0
CAPTURE_DONE = 6.55

BRIDGE_A = 7.6
BRIDGE_B = 7.95

MEETING_ASK = 9.15
MEETING_STEPS = [9.85, 10.5, 11.15]
MEETING_RESULT = 11.95

CLIENT_CARD = 14.9
CLIENT_HIGHLIGHT = 15.9
CLIENT_HIGHLIGHT_LEN = 0.75
CLIENT_INSIGHT = 16.9

TODO_SPEAK = 20.25
TODO_SPEAK_LEN = 1.35
TODO_SPLIT = 21.95
TODO_STEP = 0.32
TODO_SUMMARY = 23.35

OUTRO_LOGO = 25.25
OUTRO_WORD = 25.75
OUTRO_SLOGAN = 26.25
OUTRO_DEVICES = 27.0
OUTRO_CTA = 27.7


def sfx_events():
    """(time, kind) pairs that the audio mixer turns into sound effects."""
    ev = []
    ev += [(t, "pop") for t in HOOK_LINES]
    for name, start, _ in SCENES[1:]:
        ev.append((start - 0.12, "whoosh"))
    ev.append((2.75, "rise"))
    for i in range(len(CAPTURE_WORDS)):
        ev.append((CAPTURE_TYPE_START + i * CAPTURE_TYPE_STEP, "tick"))
    ev.append((CAPTURE_MARK, "mark"))
    ev.append((CAPTURE_CLEAN, "swipe"))
    ev.append((CAPTURE_DONE, "chime"))
    ev += [(BRIDGE_A, "pop"), (BRIDGE_B, "pop_hi")]
    ev.append((MEETING_ASK, "pop"))
    ev += [(t, "check") for t in MEETING_STEPS]
    ev.append((MEETING_RESULT, "chime"))
    ev.append((CLIENT_CARD, "pop"))
    ev.append((CLIENT_HIGHLIGHT, "marker"))
    ev.append((CLIENT_INSIGHT, "sparkle"))
    for i in range(10):
        ev.append((TODO_SPEAK + i * TODO_SPEAK_LEN / 10, "tick"))
    ev += [(TODO_SPLIT + i * TODO_STEP, "pop_hi") for i in range(3)]
    ev.append((TODO_SUMMARY, "chime"))
    ev.append((OUTRO_LOGO, "impact"))
    ev.append((OUTRO_SLOGAN, "sparkle"))
    ev.append((OUTRO_CTA, "pop"))
    return sorted(ev)
