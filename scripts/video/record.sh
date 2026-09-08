#!/usr/bin/env bash
# Start or stop a screen recording. Segments are recorded separately so the
# storyboard can splice title cards between them without frame-accurate cutting.
set -euo pipefail
case "$1" in
  start)
    out="$2"
    ffmpeg -y -f avfoundation -capture_cursor 1 -framerate 25 -i "4" \
      -vf "scale=1920:1080" -pix_fmt yuv420p -c:v libx264 -preset ultrafast -crf 18 \
      -loglevel error "$out" >/dev/null 2>&1 &
    echo $! > /tmp/factlayer_rec.pid
    sleep 2   # let the encoder settle before the action starts
    ;;
  stop)
    pid=$(cat /tmp/factlayer_rec.pid 2>/dev/null || true)
    [ -n "$pid" ] && kill -INT "$pid" 2>/dev/null || true
    sleep 2
    rm -f /tmp/factlayer_rec.pid
    ;;
esac
