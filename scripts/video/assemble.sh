#!/usr/bin/env bash
# Assemble the screencast: title cards around real screen recordings.
# Recordings are cropped to the page content (browser chrome removed) and sped up,
# since driving the UI programmatically leaves gaps a live presenter would not.
set -euo pipefail
cd "$(dirname "$0")/../.."

CROP="crop=1898:918:11:152,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x12110d"
OUT=build/fact-knowledge-layer-demo.mp4
W=build/work
rm -rf "$W"; mkdir -p "$W"

card () {  # card <stage-png> <seconds> <out>
  ffmpeg -y -loglevel error -loop 1 -i "$1" -t "$2" -r 30 \
    -vf "scale=1920:1080,format=yuv420p" -c:v libx264 -preset medium -crf 20 "$3"
}

clip () {  # clip <src> <start> <duration> <speed> <out>
  ffmpeg -y -loglevel error -ss "$2" -i "$1" -t "$3" \
    -vf "${CROP},setpts=PTS/$4,fps=30,format=yuv420p" \
    -c:v libx264 -preset medium -crf 20 "$5"
}

card build/stage/000.png 5 "$W/a.mp4"          # title
card build/stage/001.png 6 "$W/b.mp4"          # the core idea
clip build/rec/01_ingest.mp4 43 27 1.5 "$W/c.mp4"   # a PDF being processed
card build/stage/003.png 4 "$W/d.mp4"          # case 1 card, reused as a section marker
clip build/rec/02_cases.mp4 6 132 1.5 "$W/e.mp4"    # the walkthrough
card build/stage/013.png 7 "$W/f.mp4"          # closing numbers

for f in a b c d e f; do echo "file '$PWD/$W/$f.mp4'"; done > "$W/list.txt"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$W/list.txt" -c copy "$OUT"
echo "wrote $OUT  $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")s  $(du -h "$OUT" | cut -f1)"
