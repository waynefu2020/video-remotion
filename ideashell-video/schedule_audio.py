"""Music bed + SFX for the schedule video -> out/schedule-audio.wav (48 kHz stereo, no voice)."""

import os
import wave

import numpy as np

import audio as A
from audio import SR, bass, bell, clap, fft_filter, hat, hz, kick, mixs, onepole, pad, pluck, reverb, sweep_tone, tt, \
    whoosh
from schedule_timeline import AGAIN, CAL, CAL_OUT, DURATION, LOGO, MORPH, SLAM, TASK1, TASK2, TYPE1, TYPE2, \
    sfx_events

N = int(SR * DURATION)
BPM = 100
BEAT = 60 / BPM
BAR = BEAT * 4
rng = np.random.default_rng(23)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "schedule-audio.wav")
SCALE = [64, 66, 68, 71, 73, 76, 78, 80, 83, 85, 88]


def add(buf, sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N or i + len(sig) <= 0:
        return
    if i < 0:
        sig, i = sig[-i:], 0
    sig = sig[: N - i] * gain
    left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[0, i:i + len(sig)] += sig * left * 1.414
    buf[1, i:i + len(sig)] += sig * right * 1.414


def click(dur=0.02, decay=0.004):
    return np.diff(rng.normal(size=int(dur * SR)), prepend=0) * A.env(dur, 0.0005, decay)


def thump(f0=150, f1=55, dur=0.3, decay=0.08):
    t = tt(dur)
    return np.sin(2 * np.pi * np.cumsum(f1 + (f0 - f1) * np.exp(-t / 0.025)) / SR) * A.env(dur, 0.002, decay)


def key():
    body = fft_filter(rng.normal(size=int(0.05 * SR)), lo=1200, hi=7000) * A.env(0.05, 0.0005, 0.008)
    tone = thump(rng.uniform(380, 520), 240, 0.06, 0.012)
    return mixs(body * 0.45, tone * 0.25)


def make_sfx(kind):
    if kind == "key":
        return key() * 0.8, float(rng.uniform(-0.3, 0.3))
    if kind.startswith("mark"):
        i = int(kind[4:])
        f = hz(SCALE[min(i, len(SCALE) - 1)])
        tone = sweep_tone(f, f, 0.18, 0.06) * 0.3
        return mixs(thump(160, 60, 0.3, 0.09) * 0.75, tone, click() * 0.25), -0.15 + 0.05 * i
    if kind == "blow":
        out = whoosh(0.55, 1200, 9000) * 0.32
        for k in range(10):
            c = click(0.015, 0.003) * rng.uniform(0.15, 0.35)
            j = int(rng.uniform(0.02, 0.4) * SR)
            out[j:j + len(c)] += c[: len(out) - j]
        return out, 0.15
    if kind == "reflow":
        out = np.zeros(int(0.6 * SR))
        for k in range(8):
            c = mixs(click(0.012, 0.003) * 0.3, sweep_tone(1800 + 120 * k, 1800 + 120 * k, 0.03, 0.008) * 0.08)
            j = int(k * 0.05 * SR)
            out[j:j + len(c)] += c
        return out, 0.0
    if kind == "fly":
        return whoosh(0.45, 500, 6000) * 0.18, -0.2
    if kind == "tag":
        return sweep_tone(900, 1500, 0.1, 0.035) * 0.35, 0.2
    if kind == "check":
        return A.make_sfx("check")[0] * 1.1, 0.0
    if kind == "line":
        return bell([hz(76), hz(83)], 1.0, 0.35) * 0.3, 0.0
    if kind == "page":
        n = fft_filter(rng.normal(size=int(0.3 * SR)), lo=1500, hi=8000)
        t = tt(0.3)
        return n * np.sin(np.pi * t / 0.3) ** 2 * 0.22, 0.25
    if kind == "morph":
        out = np.zeros(int(1.0 * SR))
        x, k = 0.0, 0
        while x < 0.8:
            c = mixs(click(0.014, 0.003) * 0.35, thump(700, 400, 0.03, 0.006) * 0.12)
            j = int(x * SR)
            out[j:j + len(c)] += c[: len(out) - j]
            x += 0.05 * (1 - 0.6 * x / 0.8)
            k += 1
        return out, 0.0
    if kind == "tick":
        return A.make_sfx("tick")[0] * 0.9, float(rng.uniform(-0.3, 0.3))
    if kind.startswith("land"):
        i = int(kind[4:])
        return mixs(thump(130, 70, 0.22, 0.06) * 0.5, pluck(hz(SCALE[i + 2]), 0.5) * 0.3), -0.3 + 0.1 * i
    if kind == "slam":
        boom = A.make_sfx("impact")[0] * 0.8
        return mixs(boom, kick() * 0.6, clap() * 0.35), 0.0
    if kind == "slam2":
        return mixs(kick() * 0.6, clap() * 0.4, thump(200, 60, 0.4, 0.12) * 0.5) * 0.8, 0.0
    if kind.startswith("hl"):
        i = int(kind[2:])
        return mixs(sweep_tone(hz(SCALE[5 + 2 * i]), hz(SCALE[5 + 2 * i]), 0.3, 0.1) * 0.3, click() * 0.2), 0.0
    if kind == "logo":
        return mixs(A.make_sfx("pop")[0], A.make_sfx("sparkle")[0] * 0.8), 0.0
    return A.make_sfx(kind)


def chord_at(bar):
    # E - C#m - A - B
    roots = [52, 49, 57, 59]
    qualities = [(0, 4, 7, 11), (0, 3, 7, 10), (0, 4, 7, 11), (0, 4, 7, 9)]
    r = roots[bar % 4]
    return r, [r + q for q in qualities[bar % 4]]


def build_music():
    music = np.zeros((2, N))
    drums = np.zeros((2, N))
    duck = np.ones(N)
    bars = int(np.ceil(LOGO / BAR))
    for b in range(bars):
        t0 = b * BAR
        root, notes = chord_at(b)
        add(music, pad([hz(n + 12) for n in notes[:3]], min(BAR + 0.3, LOGO - t0 + 0.3)), t0, 0.12)
        for step in range(8):
            t = t0 + step * BEAT / 2
            if t >= LOGO:
                break
            in_build = CAL <= t < SLAM[0]
            seq = [0, 2, 1, 3, 2, 1, 3, 2]
            m = [notes[0] + 24, notes[1] + 24, notes[2] + 24, notes[3] + 24][seq[step]]
            add(music, pluck(hz(m), 0.45, 0.5), t, 0.08 if in_build else 0.11, pan=0.35 if step % 2 else -0.35)
            if not in_build and t >= TYPE1[1]:
                add(music, bass(hz(root - 12), BEAT / 2), t, 0.26 if step % 2 == 0 else 0.13)
        for beat in range(4):
            t = t0 + beat * BEAT
            if t >= LOGO or t < TYPE1[1] or CAL <= t < SLAM[0]:
                continue
            if beat in (0, 2):
                add(drums, kick(), t, 0.42)
                i = int(t * SR)
                d = 1 - 0.35 * np.exp(-tt(0.3) / 0.09)
                duck[i:i + len(d)] = np.minimum(duck[i:i + len(d)], d[: N - i])
            add(drums, hat(), t + BEAT / 2, 0.22, 0.25)
            if beat in (1, 3) and t >= SLAM[0]:
                add(drums, clap(), t, 0.18, -0.1)
    add(music, whoosh(SLAM[0] - MORPH, 300, 8000, rising=True) * 0.14, MORPH)
    end_root, end_notes = chord_at(0)
    add(music, pad([hz(n + 12) for n in end_notes] + [hz(end_root + 26)], DURATION - LOGO), LOGO, 0.3)
    for k, m in enumerate([76, 80, 83, 87, 88, 87, 83, 80]):
        add(music, pluck(hz(m), 1.2, 0.5), LOGO + 0.3 + k * BEAT * 0.75, 0.16, pan=-0.3 + 0.08 * k)
    add(music, bass(hz(end_root - 12), 3.0), LOGO, 0.32)
    music *= duck
    return music + drums


def main():
    music = build_music()
    sfx = np.zeros((2, N))
    for t, kind in sfx_events():
        sig, pan = make_sfx(kind)
        gain = 0.7 if kind == "key" and TYPE2[0] <= t <= TYPE2[1] else 1.0
        add(sfx, sig, t, gain, pan)
    mix = reverb(music * 0.85, mix=0.22) + reverb(sfx, seconds=0.8, mix=0.1)
    fade = np.ones(N)
    tail = int(2.0 * SR)
    fade[-tail:] = np.linspace(1, 0, tail) ** 1.5
    fade[: int(0.02 * SR)] = np.linspace(0, 1, int(0.02 * SR))
    mix *= fade
    mix /= np.max(np.abs(mix)) + 1e-9
    mix = np.tanh(mix * 2.1) / np.tanh(2.1) * 0.9
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pcm = (mix.T * 32767).astype("<i2")
    with wave.open(OUT, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(OUT)


if __name__ == "__main__":
    main()
