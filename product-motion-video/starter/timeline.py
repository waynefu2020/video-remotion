"""Shared timing for picture and sound. All times are in seconds."""

import json
import os

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
    ("hook", 0.0, 2.0),
    ("capture", 2.0, 9.4),
    ("meeting", 9.4, 15.7),
    ("client", 15.7, 20.6),
    ("todo", 20.6, 25.6),
    ("outro", 25.6, 30.0),
]


def scene_start(name):
    return next(s for n, s, _ in SCENES if n == name)


HOOK_LINES = [0.1, 0.6, 1.1]

# ---- capture: rambling voice line, then the clean-up ----
_voice = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "voice", "capture.json")))
VOICE_AT = 2.35
VOICE_PHRASES = [VOICE_AT + p["start"] for p in _voice["phrases"]]
VOICE_LENS = [p["dur"] for p in _voice["phrases"]]
VOICE_END = VOICE_AT + _voice["duration"]

# (display text, kind, phrase index, position inside the phrase 0..1)
# kind: n = keep, f = filler word, w = words the speaker took back
CAPTURE_TOKENS = [
    ("嗯…", "f", 0, 0.0),
    ("那个，", "f", 1, 0.0),
    ("下午", "n", 2, 0.0),
    ("和 Allen ", "n", 2, 0.22),
    ("的会，", "n", 2, 0.68),
    ("周四，", "w", 3, 0.0),
    ("不对，", "w", 4, 0.0),
    ("周五前", "n", 5, 0.0),
    ("把报价", "n", 5, 0.33),
    ("给他，", "n", 5, 0.68),
    ("嗯，", "f", 6, 0.0),
    ("帮我", "n", 7, 0.0),
    ("准备一下", "n", 7, 0.35),
]
CAPTURE_TOKEN_AT = [VOICE_PHRASES[p] + VOICE_LENS[p] * f for _, _, p, f in CAPTURE_TOKENS]
ZAP_START = VOICE_END + 0.12
ZAP_STEP = 0.17
CAPTURE_ZAPS = [ZAP_START + k * ZAP_STEP for k in range(sum(k == "f" for _, k, _, _ in CAPTURE_TOKENS))]
CAPTURE_CORRECT = CAPTURE_ZAPS[-1] + 0.2
CAPTURE_COLLAPSE = CAPTURE_CORRECT + 0.3
CAPTURE_COUNT = CAPTURE_COLLAPSE + 0.2
CAPTURE_NOTE = CAPTURE_COLLAPSE + 0.5

# ---- meeting: search across the note wall ----
M0 = scene_start("meeting")
MEETING_ASK = M0 + 0.35
WALL_IN = M0 + 0.75
WALL_ZOOM = 0.75
SCAN_START = WALL_IN + 0.3
SCAN_LEN = 0.85
WALL_FILTER = SCAN_START + SCAN_LEN + 0.05
WALL_PICKS = [WALL_FILTER + 0.12 + i * 0.15 for i in range(4)]
WALL_FLY = WALL_PICKS[-1] + 0.3
WALL_OUT = WALL_FLY - 0.1
MEETING_RESULT = WALL_FLY + 0.15

C0 = scene_start("client")
CLIENT_CARD = C0 + 0.8
CLIENT_HIGHLIGHT = C0 + 1.7
CLIENT_HIGHLIGHT_LEN = 0.7
CLIENT_INSIGHT = C0 + 2.6

T0 = scene_start("todo")
TODO_SPEAK = T0 + 0.65
TODO_SPEAK_LEN = 1.3
TODO_SPLIT = T0 + 2.2
TODO_STEP = 0.3
TODO_SUMMARY = T0 + 3.5

O0 = scene_start("outro")
OUTRO_LOGO = O0 + 0.2
OUTRO_WORD = O0 + 0.65
OUTRO_SLOGAN = O0 + 1.1


def sfx_events():
    """(time, kind) pairs that the audio mixer turns into sound effects."""
    ev = [(t, "pop") for t in HOOK_LINES]
    for name, start, _ in SCENES[1:]:
        ev.append((start - 0.12, "whoosh"))
    ev.append((2.2, "rise"))
    ev += [(t, "tick") for t in CAPTURE_TOKEN_AT]
    ev += [(t, f"zap{i}") for i, t in enumerate(CAPTURE_ZAPS)]
    ev.append((CAPTURE_CORRECT, "mark"))
    ev.append((CAPTURE_COLLAPSE, "snap"))
    ev.append((CAPTURE_NOTE, "chime"))

    ev.append((MEETING_ASK, "pop"))
    ev.append((WALL_IN, "drop"))
    ev.append((SCAN_START, "flutter"))
    ev += [(t, f"ping{i}") for i, t in enumerate(WALL_PICKS)]
    ev.append((WALL_FLY, "swipe"))
    ev.append((MEETING_RESULT + 0.1, "chime"))

    ev.append((CLIENT_CARD, "pop"))
    ev.append((CLIENT_HIGHLIGHT, "marker"))
    ev.append((CLIENT_INSIGHT, "sparkle"))
    for i in range(10):
        ev.append((TODO_SPEAK + i * TODO_SPEAK_LEN / 10, "tick"))
    ev += [(TODO_SPLIT + i * TODO_STEP, "pop_hi") for i in range(3)]
    ev.append((TODO_SUMMARY, "chime"))
    ev.append((OUTRO_LOGO, "impact"))
    ev.append((OUTRO_SLOGAN, "sparkle"))
    return sorted(ev)
