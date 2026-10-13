"""Synthesize the rambling voice line for the capture scene with Piper (offline TTS).

Writes assets/voice/capture.wav and assets/voice/capture.json (phrase start times
relative to the start of the clip). The outputs are committed, so build.sh does
not need Piper; rerun this only when the line changes.
"""

import json
import os
import subprocess
import urllib.request
import wave

import numpy as np
from piper import PiperVoice, SynthesisConfig

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(ROOT, "models")
OUT_DIR = os.path.join(ROOT, "assets", "voice")
MODEL = "zh_CN-huayan-medium"
TEMPO = 1.15
BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/"

# (spoken text, length_scale, pause after in seconds)
PHRASES = [
    ("嗯……", 1.1, 0.08),
    ("那个，", 0.85, 0.04),
    ("下午和艾伦的会，", 0.72, 0.03),
    ("周四，", 0.8, 0.0),
    ("不对，", 0.72, 0.0),
    ("周五前把报价给他，", 0.7, 0.03),
    ("嗯，", 0.9, 0.02),
    ("帮我准备一下。", 0.74, 0.0),
]


def ensure_model():
    os.makedirs(MODEL_DIR, exist_ok=True)
    for suffix in (".onnx", ".onnx.json"):
        path = os.path.join(MODEL_DIR, MODEL + suffix)
        if not os.path.exists(path):
            urllib.request.urlretrieve(BASE + MODEL + suffix, path)
    return os.path.join(MODEL_DIR, MODEL + ".onnx")


def trim(x, sr, thresh=0.02):
    loud = np.where(np.abs(x) > thresh)[0]
    if not len(loud):
        return x
    pad = int(0.015 * sr)
    return x[max(0, loud[0] - pad): loud[-1] + pad]


def main():
    voice = PiperVoice.load(ensure_model())
    sr = voice.config.sample_rate
    clip, timings, cursor = [], [], 0.0
    for text, scale, pause in PHRASES:
        cfg = SynthesisConfig(length_scale=scale, noise_scale=0.6, noise_w_scale=0.8)
        audio = np.concatenate([c.audio_float_array for c in voice.synthesize(text, cfg)])
        audio = trim(audio, sr)
        timings.append({"text": text, "start": round(cursor, 3), "dur": round(len(audio) / sr, 3)})
        clip += [audio, np.zeros(int(pause * sr), dtype=np.float32)]
        cursor += len(audio) / sr + pause
    out = np.concatenate(clip)
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.9

    os.makedirs(OUT_DIR, exist_ok=True)
    raw = os.path.join(OUT_DIR, "capture-raw.wav")
    with wave.open(raw, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((out * 32767).astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", f"atempo={TEMPO}",
                    os.path.join(OUT_DIR, "capture.wav")], check=True)
    os.remove(raw)
    for p in timings:
        p["start"] = round(p["start"] / TEMPO, 3)
        p["dur"] = round(p["dur"] / TEMPO, 3)
    with open(os.path.join(OUT_DIR, "capture.json"), "w") as f:
        json.dump({"sample_rate": sr, "duration": round(len(out) / sr / TEMPO, 3), "phrases": timings}, f,
                  ensure_ascii=False, indent=1)
    print(json.dumps(timings, ensure_ascii=False))
    print("total", round(len(out) / sr / TEMPO, 2))


if __name__ == "__main__":
    main()
