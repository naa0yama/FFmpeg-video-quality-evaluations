#!/usr/bin/env bash
set -eu

EVALUATIONTARGET="${1:-/dist/x264_x264_crf23_medium.mp4}"
BASEFILE="${2:-/dist/base.mp4}"
SUFFIX="${3:-.mp4}"
OUTPUTDIR="/dist"
CPU_THREADS="$(getconf _NPROCESSORS_ONLN)"

set -x

for __filetype in "csv" "json"
do
  FILENAME="$(basename "${EVALUATIONTARGET}" "${SUFFIX}")"
  ffmpeg -hide_banner -i "${EVALUATIONTARGET}" -i "${BASEFILE}" \
    -lavfi libvmaf=\'model=version=vmaf_v0.6.1\\:name=vmaf:feature=name=float_ssim:n_threads=${CPU_THREADS}:log_fmt=${__filetype}:log_path=${OUTPUTDIR}/${FILENAME}_vmaf.${__filetype}\' -an -t 5 -f null -
done
