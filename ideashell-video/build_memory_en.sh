#!/usr/bin/env bash
# Overseas (English) cut of the memory video -> dist/en/ideashell-memory-en.mp4
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p fonts out dist/en
for w in Regular Medium Bold Black; do
  [ -s "fonts/Inter-$w.ttf" ] && continue
  curl -fsSL -o /tmp/inter.zip https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip
  unzip -o -q -j /tmp/inter.zip "extras/ttf/Inter-Regular.ttf" "extras/ttf/Inter-Medium.ttf" \
    "extras/ttf/Inter-Bold.ttf" "extras/ttf/Inter-Black.ttf" -d fonts
  break
done
export VIDEO_LANG=en
python3 memory_audio.py
python3 memory_render.py "$@"
ffmpeg -y -loglevel error -i out/memory-video-en.mp4 -i out/memory-audio.wav \
  -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart out/ideashell-memory-en.mp4
cp out/ideashell-memory-en.mp4 dist/en/ideashell-memory-en.mp4
python3 memory_cover_en.py
echo "dist/en/ideashell-memory-en.mp4"
