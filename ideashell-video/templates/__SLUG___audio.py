"""Music bed + SFX for the「__TITLE__」video -> out/__SLUG__-audio.wav (48 kHz stereo, no voice)."""

import os
import wave

import numpy as np

import audio as A
from audio import SR, bass, hat, hz, kick, mixs, pad, pluck, reverb
from __SLUG___timeline import BPM, DURATION, LOGO, POINT_AT, sfx_events

N = int(SR * DURATION)
BEAT = 60 / BPM
BAR = BEAT * 4
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "__SLUG__-audio.wav")


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


def make_sfx(kind):
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
    for b in range(int(np.ceil(LOGO / BAR))):
        t0 = b * BAR
        root, notes = chord_at(b)
        add(music, pad([hz(n + 12) for n in notes[:3]], min(BAR + 0.3, LOGO - t0 + 0.3)), t0, 0.12)
        for step in range(8):
            t = t0 + step * BEAT / 2
            if t >= LOGO:
                break
            m = notes[[0, 2, 1, 3, 2, 1, 3, 2][step]] + 24
            add(music, pluck(hz(m), 0.45, 0.5), t, 0.11, pan=0.35 if step % 2 else -0.35)
            if t >= POINT_AT[0]:
                add(music, bass(hz(root - 12), BEAT / 2), t, 0.26 if step % 2 == 0 else 0.13)
        for beat in range(4):
            t = t0 + beat * BEAT
            if POINT_AT[0] <= t < LOGO:
                if beat in (0, 2):
                    add(music, kick(), t, 0.42)
                add(music, hat(), t + BEAT / 2, 0.22, 0.25)
    root, notes = chord_at(0)
    add(music, pad([hz(n + 12) for n in notes], DURATION - LOGO), LOGO, 0.3)
    add(music, bass(hz(root - 12), 3.0), LOGO, 0.32)
    return music


def main():
    music = build_music()
    sfx = np.zeros((2, N))
    for t, kind in sfx_events():
        sig, pan = make_sfx(kind)
        add(sfx, sig, t, 1.0, pan)
    mix = reverb(music * 0.85, mix=0.22) + reverb(sfx, seconds=0.8, mix=0.1)
    fade = np.ones(N)
    tail = int(1.5 * SR)
    fade[-tail:] = np.linspace(1, 0, tail) ** 1.5
    fade[: int(0.02 * SR)] = np.linspace(0, 1, int(0.02 * SR))
    mix *= fade
    mix /= np.max(np.abs(mix)) + 1e-9
    mix = np.tanh(mix * 3.2) / np.tanh(3.2) * 0.9
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
