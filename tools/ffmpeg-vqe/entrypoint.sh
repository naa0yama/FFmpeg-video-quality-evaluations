#!/usr/bin/env bash

set -eu

echo "Create base.mp4"
ffmpeg -t 5 -i /source/bbb_original.mp4 -vcodec copy -an -y /dist/base.mp4

time ffmpeg -i /dist/base.mp4 -crf 23 -preset medium -c:v libx264 -y /dist/x264_x264_crf23_medium.mp4
time ffmpeg -i /dist/base.mp4 -crf 28 -preset medium -c:v libx265 -y /dist/x265_x265_crf28_medium.mp4 -tag:v hvc1

find /dist ! -name 'base.mp4' -name '*.mp4' -print0 -exec bash /app/encode.sh {} \;
