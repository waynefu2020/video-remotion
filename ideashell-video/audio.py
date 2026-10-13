"""Synthesize the music bed and UI sound effects -> out/audio.wav (48 kHz stereo)."""

import os
import wave

import numpy as np

from timeline import BPM, DURATION, SCAN_LEN, SCENES, WALL_IN, WALL_PICKS, scene_start, sfx_events

SR = 48000
N = int(SR * DURATION)
BEAT = 60 / BPM
BAR = BEAT * 4
rng = np.random.default_rng(7)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "audio.wav")


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def env(dur, attack=0.004, decay=0.2):
    t = tt(dur)
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


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


def onepole(x, cutoff):
    """Lowpass with a per-sample (or scalar) cutoff in Hz."""
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def fft_filter(x, lo=None, hi=None):
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    gain = np.ones_like(f)
    if lo:
        gain *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        gain *= 1 / np.sqrt(1 + (f / hi) ** 4)
    return np.fft.irfft(spec * gain, len(x))


# ---------- instruments ----------

def pluck(freq, dur=0.5, bright=1.0):
    t = tt(dur)
    s = np.sin(2 * np.pi * freq * t) + 0.35 * bright * np.sin(4 * np.pi * freq * t) * np.exp(-t / 0.08)
    s += 0.12 * bright * np.sin(6 * np.pi * freq * t) * np.exp(-t / 0.04)
    return s * env(dur, 0.003, 0.22)


def pad(freqs, dur):
    t = tt(dur)
    s = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0.12):
            ff = f * 2 ** (det / 12)
            for n in range(1, 6):
                s += np.sin(2 * np.pi * ff * n * t + rng.uniform(0, 6.28)) / n ** 1.6
    shape = np.minimum(1, t / 0.35) * np.minimum(1, (dur - t) / 0.3).clip(0)
    return s * shape / (len(freqs) * 4)


def bass(freq, dur):
    t = tt(dur)
    s = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(4 * np.pi * freq * t)
    return s * env(dur, 0.006, 0.18)


def kick():
    t = tt(0.4)
    f = 45 + 95 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.16) + 0.25 * rng.normal(size=len(t)) * np.exp(-t / 0.004)


def hat():
    n = rng.normal(size=int(0.06 * SR))
    return np.diff(n, prepend=0) * env(0.06, 0.001, 0.018) * 0.5


def clap():
    n = fft_filter(rng.normal(size=int(0.25 * SR)), lo=900, hi=5000)
    t = tt(0.25)
    e = np.exp(-t / 0.07) * (1 + 0.6 * (np.sin(2 * np.pi * 90 * t) > 0) * (t < 0.03))
    return n * e * 0.9


# ---------- sfx ----------

def sweep_tone(f0, f1, dur, decay, sweep=0.04):
    t = tt(dur)
    f = f1 + (f0 - f1) * np.exp(-t / sweep)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(dur, 0.002, decay)


def whoosh(dur=0.38, lo=300, hi=5000, rising=False):
    t = tt(dur)
    x = t / dur
    cut = lo + (hi - lo) * (x if rising else np.sin(np.pi * x))
    n = onepole(rng.normal(size=len(t)), cut)
    shape = np.sin(np.pi * x) ** (1.5 if not rising else 0.6)
    if rising:
        shape *= np.minimum(1, (1 - x) * 12)
    return n * shape * 1.6


def bell(freqs, dur=1.2, decay=0.45):
    t = tt(dur)
    s = np.zeros_like(t)
    for k, f in enumerate(freqs):
        s += np.sin(2 * np.pi * f * t) * np.exp(-t / decay) / (k + 1) ** 0.5
        s += 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / (decay * 0.3))
    return s * np.minimum(1, t / 0.002) / len(freqs)


def mixs(*parts):
    n = max(len(p) for p in parts)
    return sum(np.pad(p, (0, n - len(p))) for p in parts)


def flutter(dur):
    out = np.zeros(int(dur * SR) + SR // 10)
    t = 0.0
    k = 0
    while t < dur:
        click = np.diff(rng.normal(size=int(0.012 * SR)), prepend=0) * env(0.012, 0.0005, 0.003)
        tone = sweep_tone(1800 + 900 * (t / dur) + rng.uniform(-200, 200), 2400, 0.02, 0.005) * 0.4
        sig = mixs(click, tone) * (0.5 + 0.5 * t / dur)
        i = int(t * SR)
        out[i:i + len(sig)] += sig
        t += lerp_gap(t / dur)
        k += 1
    return out


def lerp_gap(x):
    return 0.07 * (1 - x) + 0.018 * x


def make_sfx(kind):
    if kind.startswith("zap"):
        i = int(kind[3:])
        f = 640 * 1.26 ** i
        pff = fft_filter(rng.normal(size=int(0.08 * SR)), lo=2000, hi=9000) * env(0.08, 0.001, 0.02)
        return mixs(sweep_tone(f, f * 2.1, 0.16, 0.05) * 0.55, pff * 0.25), (-0.25 + 0.25 * i)
    if kind.startswith("ping"):
        i = int(kind[4:])
        return bell([hz([86, 90, 93, 98][i])], 0.7, 0.22) * 0.55, (-0.4 + 0.27 * i)
    if kind == "snap":
        t = tt(0.3)
        thump = np.sin(2 * np.pi * np.cumsum(60 + 140 * np.exp(-t / 0.03)) / SR) * env(0.3, 0.002, 0.09)
        click = np.diff(rng.normal(size=int(0.02 * SR)), prepend=0) * env(0.02, 0.0005, 0.004)
        return mixs(thump * 0.8, click * 0.6), 0.0
    if kind == "drop":
        t = tt(0.9)
        sub = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t / 0.15)) / SR) * env(0.9, 0.01, 0.35)
        return mixs(whoosh(0.6, 2500, 300) * 0.25, sub * 0.6), 0.0
    if kind == "flutter":
        return flutter(SCAN_LEN) * 0.45, 0.0
    if kind == "pop":
        return sweep_tone(520, 1050, 0.14, 0.05) * 0.6, 0.0
    if kind == "pop_hi":
        return sweep_tone(800, 1600, 0.12, 0.04) * 0.5, 0.0
    if kind == "tick":
        n = np.diff(rng.normal(size=int(0.02 * SR)), prepend=0) * env(0.02, 0.0005, 0.004)
        return mixs(n * 0.5, sweep_tone(2600, 2600, 0.03, 0.006) * 0.2), float(rng.uniform(-0.3, 0.3))
    if kind == "whoosh":
        return whoosh() * 0.22, 0.0
    if kind == "swipe":
        return whoosh(0.28, 800, 7000) * 0.18, 0.2
    if kind == "rise":
        return whoosh(0.9, 400, 6000, rising=True) * 0.18, 0.0
    if kind == "mark":
        t = tt(0.22)
        sq = np.sign(np.sin(2 * np.pi * 220 * t)) * 0.3 + np.sin(2 * np.pi * 330 * t)
        gate = ((t < 0.07) | ((t > 0.11) & (t < 0.18))).astype(float)
        return onepole(sq * gate, 2500) * env(0.22, 0.002, 0.2) * 0.35, 0.0
    if kind == "check":
        return mixs(sweep_tone(1200, 1900, 0.18, 0.06) * 0.35, bell([hz(93)], 0.4, 0.12) * 0.25), 0.0
    if kind == "chime":
        s = bell([hz(86), hz(90), hz(93)], 1.6, 0.5)
        s2 = np.concatenate([np.zeros(int(0.07 * SR)), bell([hz(98)], 1.4, 0.45)])
        s = mixs(s, 0.6 * s2)
        return s * 0.45, 0.0
    if kind == "marker":
        t = tt(0.75)
        n = fft_filter(rng.normal(size=len(t)), lo=1800, hi=6000)
        wob = 0.6 + 0.4 * np.sin(2 * np.pi * 11 * t)
        return n * wob * np.minimum(1, t / 0.03) * np.minimum(1, (0.75 - t) / 0.08) * 0.13, -0.1
    if kind == "sparkle":
        out = np.zeros(int(0.9 * SR))
        for k, m in enumerate([86, 90, 93, 98, 102]):
            b = bell([hz(m)], 0.6, 0.18)
            i = int(k * 0.045 * SR)
            out[i:i + len(b)] += b[: len(out) - i]
        return out * 0.26, 0.15
    if kind == "impact":
        t = tt(1.6)
        f = 32 + 70 * np.exp(-t / 0.08)
        boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.5)
        noise = onepole(rng.normal(size=len(t)), 2500) * np.exp(-t / 0.25) * 0.6
        return mixs(boom * 0.9, noise * 0.5, bell([hz(74), hz(81), hz(86)], 1.6, 0.7) * 0.5) * 0.38, 0.0
    raise ValueError(kind)


# ---------- arrangement ----------

def chord_at(bar):
    # D - A - Bm - G
    roots = [62, 57, 59, 55]
    qualities = [(0, 4, 7), (0, 4, 7), (0, 3, 7), (0, 4, 7)]
    r = roots[bar % 4]
    return r, [r + q for q in qualities[bar % 4]]


def section(t):
    for name, start, end in SCENES:
        if start <= t < end:
            return name
    return SCENES[-1][0]


def build_music():
    music = np.zeros((2, N))
    drums = np.zeros((2, N))
    duck = np.ones(N)
    bars = int(np.ceil(DURATION / BAR))
    outro_start = SCENES[-1][1]

    for b in range(bars):
        t0 = b * BAR
        root, notes = chord_at(b)
        if t0 < outro_start:
            add(music, pad([hz(n) for n in notes], BAR + 0.3), t0, 0.16)
        for step in range(8):
            t = t0 + step * BEAT / 2
            if t >= outro_start:
                break
            sec = section(t)
            seq = [0, 1, 2, 1, 2, 3, 2, 1]
            octave = [notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[0] + 24]
            m = octave[seq[step] % 4]
            gain = 0.17
            if WALL_IN <= t < WALL_PICKS[0]:
                gain = 0.07
            add(music, pluck(hz(m), 0.5), t, gain, pan=0.35 if step % 2 else -0.35)
            if sec != "hook" and not (WALL_IN <= t < WALL_PICKS[0]):
                add(music, bass(hz(root - 24), BEAT / 2), t, 0.32 if step % 2 == 0 else 0.18)

        for beat in range(4):
            t = t0 + beat * BEAT
            if t >= outro_start:
                break
            sec = section(t)
            if sec == "hook" or WALL_IN - 0.05 <= t < WALL_PICKS[0] - 0.02:
                continue
            k = kick()
            add(drums, k, t, 0.6)
            i = int(t * SR)
            d = 1 - 0.45 * np.exp(-tt(0.3) / 0.09)
            duck[i:i + len(d)] = np.minimum(duck[i:i + len(d)], d[: N - i])
            if sec != "capture":
                add(drums, hat(), t + BEAT / 2, 0.35, 0.25)
                if beat in (1, 3):
                    add(drums, clap(), t, 0.22, -0.1)

    end_root, end_notes = chord_at(0)
    add(music, pad([hz(n) for n in end_notes] + [hz(end_root + 12)], DURATION - outro_start), outro_start, 0.34)
    for k, m in enumerate([74, 78, 81, 86, 81, 78, 74]):
        add(music, pluck(hz(m), 1.2, 0.6), outro_start + 0.5 + k * BEAT, 0.22, pan=-0.3 + 0.1 * k)
    add(music, bass(hz(end_root - 24), 2.5), outro_start, 0.35)

    music *= duck
    riser = whoosh(1.0, 300, 7000, rising=True) * 0.12
    add(music, riser, scene_start("meeting") - 1.0)
    return music + drums


def reverb(x, seconds=1.6, mix=0.18):
    ir_len = int(seconds * SR)
    t = np.arange(ir_len) / SR
    wet = np.zeros_like(x)
    size = 1 << int(np.ceil(np.log2(x.shape[1] + ir_len)))
    for ch in range(2):
        ir = rng.normal(size=ir_len) * np.exp(-t / (seconds / 5))
        ir = fft_filter(ir, hi=6000)
        ir /= np.sqrt(np.sum(ir ** 2))
        y = np.fft.irfft(np.fft.rfft(x[ch], size) * np.fft.rfft(ir, size), size)[: x.shape[1]]
        wet[ch] = y
    return x + wet * mix


def main():
    music = build_music()
    sfx = np.zeros((2, N))
    for t, kind in sfx_events():
        sig, pan = make_sfx(kind)
        add(sfx, sig, t, 1.0, pan)

    mix = reverb(music * 0.85, mix=0.22) + reverb(sfx, seconds=0.9, mix=0.12)
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
