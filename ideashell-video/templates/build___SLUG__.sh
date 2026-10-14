#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p fonts out
for w in Regular Medium Bold Black; do
  f="fonts/NotoSansSC-$w.otf"
  [ -s "$f" ] || curl -fsSL -o "$f" "https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/SC/NotoSansSC-$w.otf"
done

python3 __SLUG___audio.py
python3 __SLUG___render.py "$@"
ffmpeg -y -loglevel error -i out/__SLUG__-video.mp4 -i out/__SLUG__-audio.wav \
  -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart out/ideashell-__SLUG__.mp4
mkdir -p dist && cp out/ideashell-__SLUG__.mp4 dist/ideashell-__SLUG__.mp4
echo "dist/ideashell-__SLUG__.mp4"
