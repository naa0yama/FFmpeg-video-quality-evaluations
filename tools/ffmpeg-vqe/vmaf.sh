#!/usr/bin/env bash
set -eu

EVALUATIONFILE="${1}"
BASEFILE="${6:-/dist/base.mp4}"
SUFFIX="${7:-.mp4}"
OUTPUTDIR="/dist"
CPU_THREADS="$(getconf _NPROCESSORS_ONLN)"

set -x


for __filetype in "json"
do
  FILENAME="$(basename "${EVALUATIONFILE}" "${SUFFIX}")"

  # VMAF
  ffmpeg -hide_banner -i "${EVALUATIONFILE}" -i "${BASEFILE}" \
    -lavfi libvmaf=\'model=version=vmaf_v0.6.1\\:name=vmaf:feature=name=float_ssim:n_threads=${CPU_THREADS}:log_fmt=${__filetype}:log_path=${OUTPUTDIR}/${FILENAME}_vmaf.${__filetype}\' -an -t 5 -f null -
done
