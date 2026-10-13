"""Music bed + SFX for the memory video -> out/memory-audio.wav (48 kHz stereo, no voice)."""

import os
import wave

import numpy as np

import audio as A
from audio import SR, bass, bell, clap, fft_filter, flutter, hat, hz, kick, mixs, onepole, pad, pluck, reverb, \
    sweep_tone, tt, whoosh
from memory_timeline import (BPM, CH2, DURATION, FLIGHT_END, FLIGHT_START, OUT_FORM, OUT_LOGO, RIFFLE_END,
                             RIFFLE_START, SHATTER, SILENCE_END, ABSORB_START, sfx_events)

N = int(SR * DURATION)
BEAT = 60 / BPM
BAR = BEAT * 4
DROP = 4.6
rng = np.random.default_rng(11)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "memory-audio.wav")


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


def thump(f0=140, f1=50, dur=0.35, decay=0.1):
    t = tt(dur)
    return np.sin(2 * np.pi * np.cumsum(f1 + (f0 - f1) * np.exp(-t / 0.03)) / SR) * A.env(dur, 0.002, decay)


def make_sfx(kind):
    if kind == "type":
        tone = sweep_tone(1500 + rng.uniform(-200, 300), 1200, 0.04, 0.01)
        return mixs(click(0.03, 0.006) * 0.35, tone * 0.08), float(rng.uniform(-0.25, 0.25))
    if kind == "shatter":
        out = np.zeros(int(1.2 * SR))
        for k in range(14):
            b = bell([rng.uniform(2200, 6500)], 0.5, rng.uniform(0.06, 0.18))
            i = int(rng.uniform(0, 0.12) * SR)
            out[i:i + len(b)] += b[: len(out) - i] * rng.uniform(0.4, 1)
        burst = fft_filter(rng.normal(size=int(0.5 * SR)), lo=2500) * A.env(0.5, 0.001, 0.09)
        return mixs(out * 0.22, burst * 0.22, thump(180, 60, 0.4, 0.12) * 0.5), 0.0
    if kind == "tunnel":
        dur = FLIGHT_END - FLIGHT_START + 0.12
        t = tt(dur)
        x = t / dur
        rumble = onepole(rng.normal(size=len(t)), 120 + 500 * x) * 2.2
        sub = np.sin(2 * np.pi * np.cumsum(40 + 50 * x ** 2) / SR)
        air = whoosh(dur, 300, 9000, rising=True)
        shape = np.minimum(1, t / 0.15) * (0.4 + 0.6 * x ** 1.5)
        return mixs(rumble * shape * 0.22, sub * shape * 0.35, air * 0.3), 0.0
    if kind == "whoosh_in":
        return whoosh(0.38, 6000, 400)[::-1] * 0.22, 0.0
    if kind == "slam":
        k = kick() * 0.9
        body = onepole(rng.normal(size=int(0.3 * SR)), 1800) * A.env(0.3, 0.001, 0.06)
        return mixs(k, body * 0.5, clap() * 0.4) * 0.55, 0.0
    if kind == "chapter":
        return mixs(whoosh(0.32, 900, 8000) * 0.18, thump(110, 45, 0.5, 0.16) * 0.5), 0.0
    if kind == "form":
        out = np.zeros(int(1.2 * SR))
        for k, m in enumerate([74, 78, 81, 86, 90, 93]):
            b = bell([hz(m)], 0.7, 0.2)
            i = int(k * 0.05 * SR)
            out[i:i + len(b)] += b[: len(out) - i]
        return mixs(out * 0.2, whoosh(0.6, 400, 5000, rising=True) * 0.12), 0.0
    if kind == "zap":
        return A.make_sfx("zap2")[0] * 1.1, 0.0
    if kind == "step":
        return mixs(sweep_tone(900, 1350, 0.1, 0.03) * 0.35, click() * 0.2), 0.0
    if kind == "whip":
        return whoosh(0.22, 1500, 9000) * 0.24, 0.25
    if kind == "fly_in":
        return whoosh(0.32, 600, 6500) * 0.16, float(rng.uniform(-0.5, 0.5))
    if kind == "scan":
        t = tt(0.24)
        s = np.sin(2 * np.pi * np.cumsum(1400 + 1600 * t / 0.24) / SR) * np.sin(np.pi * t / 0.24)
        return s * 0.07, 0.0
    if kind == "gulp":
        return mixs(sweep_tone(520, 160, 0.2, 0.06, sweep=0.05) * 0.5, thump(90, 50, 0.25, 0.08) * 0.3), 0.0
    if kind == "riffle":
        return flutter(RIFFLE_END - RIFFLE_START) * 0.5, 0.1
    if kind == "thud":
        return mixs(thump(120, 45, 0.45, 0.13) * 0.7, click(0.03, 0.006) * 0.4), 0.0
    if kind == "inhale":
        dur = OUT_LOGO - OUT_FORM - 0.45
        rev = bell([hz(81), hz(86), hz(90)], dur, dur / 2.5)[::-1]
        return mixs(whoosh(dur, 300, 7000, rising=True) * 0.22, rev * 0.25), 0.0
    return A.make_sfx(kind)


def chord_at(bar):
    # Bm - G - D - A
    roots = [59, 55, 62, 57]
    qualities = [(0, 3, 7), (0, 4, 7), (0, 4, 7), (0, 4, 7)]
    r = roots[bar % 4]
    return r, [r + q for q in qualities[bar % 4]]


def build_music():
    music = np.zeros((2, N))
    drums = np.zeros((2, N))
    duck = np.ones(N)

    # hook: dark drone under the question, ticking 16ths during the flight
    r, notes = chord_at(0)
    add(music, pad([hz(n - 12) for n in notes], FLIGHT_END + 0.1), 0.0, 0.2)
    add(music, bass(hz(r - 24), 1.2), SHATTER, 0.4)
    k = 0
    t = FLIGHT_START
    while t < FLIGHT_END - 0.02:
        add(drums, hat(), t, 0.18 + 0.25 * (t - FLIGHT_START), 0.3 if k % 2 else -0.3)
        t += 0.125 - 0.06 * (t - FLIGHT_START) / (FLIGHT_END - FLIGHT_START)
        k += 1
    add(music, pad([hz(n) for n in notes] + [hz(r + 12)], DROP - SILENCE_END + 0.2), SILENCE_END + 0.25, 0.22)

    groove_end = OUT_FORM
    breakdown = (CH2, ABSORB_START)
    bars = int(np.ceil((groove_end - DROP) / BAR))
    for b in range(bars):
        t0 = DROP + b * BAR
        root, notes = chord_at(b)
        add(music, pad([hz(n) for n in notes], min(BAR + 0.3, groove_end - t0 + 0.3)), t0, 0.15)
        for step in range(8):
            t = t0 + step * BEAT / 2
            if t >= groove_end:
                break
            seq = [0, 2, 1, 3, 2, 1, 3, 2]
            octave = [notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[0] + 24]
            in_break = breakdown[0] <= t < breakdown[1]
            add(music, pluck(hz(octave[seq[step]]), 0.5, 0.6 if in_break else 1.0), t, 0.15,
                pan=0.35 if step % 2 else -0.35)
            if not in_break:
                add(music, bass(hz(root - 24), BEAT / 2), t, 0.32 if step % 2 == 0 else 0.18)
        for beat in range(4):
            t = t0 + beat * BEAT
            if t >= groove_end or breakdown[0] <= t < breakdown[1]:
                continue
            add(drums, kick(), t, 0.6)
            i = int(t * SR)
            d = 1 - 0.45 * np.exp(-tt(0.3) / 0.09)
            duck[i:i + len(d)] = np.minimum(duck[i:i + len(d)], d[: N - i])
            add(drums, hat(), t + BEAT / 2, 0.32, 0.25)
            if beat in (1, 3):
                add(drums, clap(), t, 0.2, -0.1)
            if RIFFLE_START <= t < RIFFLE_END or t >= groove_end - BAR:
                add(drums, hat(), t + BEAT / 4, 0.18, -0.25)
                add(drums, hat(), t + 3 * BEAT / 4, 0.18, -0.25)

    add(music, whoosh(0.85, 300, 7000, rising=True) * 0.12, ABSORB_START - 0.85)

    end_root, end_notes = chord_at(2)
    add(music, pad([hz(n) for n in end_notes] + [hz(end_root + 12)], DURATION - OUT_LOGO), OUT_LOGO, 0.34)
    for k, m in enumerate([74, 78, 81, 86, 81, 78, 74]):
        add(music, pluck(hz(m), 1.2, 0.6), OUT_LOGO + 0.45 + k * BEAT, 0.2, pan=-0.3 + 0.1 * k)
    add(music, bass(hz(end_root - 24), 2.5), OUT_LOGO, 0.35)

    music *= duck
    return music + drums


def gate():
    g = np.ones(N)
    a, b = int(FLIGHT_END * SR), int(SILENCE_END * SR)
    f = int(0.015 * SR)
    g[a - f:a] = np.linspace(1, 0, f)
    g[a:b] = 0
    return g


def main():
    music = build_music()
    sfx = np.zeros((2, N))
    late = np.zeros((2, N))
    for t, kind in sfx_events():
        sig, pan = make_sfx(kind)
        add(late if t >= SILENCE_END - 0.01 and t < SILENCE_END + 0.01 else sfx, sig, t, 1.0, pan)

    mix = reverb(music * 0.85, mix=0.22) + reverb(sfx, seconds=0.9, mix=0.12)
    mix = mix * gate() + reverb(late, seconds=0.9, mix=0.12)
    fade = np.ones(N)
    tail = int(1.2 * SR)
    fade[-tail:] = np.linspace(1, 0, tail) ** 1.5
    fade[: int(0.02 * SR)] = np.linspace(0, 1, int(0.02 * SR))
    mix *= fade
    mix /= np.max(np.abs(mix)) + 1e-9
    mix = np.tanh(mix * 1.6) / np.tanh(1.6) * 0.9

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
