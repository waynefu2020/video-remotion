#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p fonts out
for w in Regular Medium Bold Black; do
  f="fonts/NotoSansSC-$w.otf"
  [ -s "$f" ] || curl -fsSL -o "$f" "https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/SC/NotoSansSC-$w.otf"
done

python3 memory_audio.py
python3 memory_render.py "$@"
ffmpeg -y -loglevel error -i out/memory-video.mp4 -i out/memory-audio.wav \
  -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart out/ideashell-memory.mp4
mkdir -p dist && cp out/ideashell-memory.mp4 dist/ideashell-memory.mp4
echo "dist/ideashell-memory.mp4"
