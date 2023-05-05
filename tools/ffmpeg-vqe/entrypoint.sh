#!/usr/bin/env bash

set -eu
CONFIG_FILE="${1:-/source/encode_config.json}"
RESULT_JSON="result.json"
OUTPUTDIR="/dist"

FFMPEG_PRESET="medium"

echo "Create base.mp4"
ffmpeg -t 5 -i /source/bbb_original.mp4 -vcodec copy -an -y /dist/base.mp4

#time ffmpeg -i /dist/base.mp4 -crf 23 -preset medium -c:v libx264 -y /dist/x264_x264_crf23_medium.mp4
#time ffmpeg -i /dist/base.mp4 -crf 28 -preset medium -c:v libx265 -y /dist/x265_x265_crf28_medium.mp4 -tag:v hvc1

cat ${CONFIG_FILE} | jq -c '.[]' |
while read -r array; do
  __name_prefix=$(echo "${array}" | jq -r '.name_prefix')
  __filename="${__name_prefix}_crf${__crf}_${FFMPEG_PRESET}"
  __codec_name=$(echo "${array}" | jq -r '.codec_name')
  __options=$(echo "${array}" | jq -r '.options')

  for __crf in $(seq -w 18 1 34)
  do
    echo ${__filename}, options ${__options}
  done
done

# VMAF
# find /dist ! -name 'base.mp4' -name '*.mp4' -print0 -exec bash /app/encode.sh {} \;

RESULT_JSON="result.json"
echo '[]' > "${RESULT_JSON}"
__result_row=$(cat <<-EOF
.+[{
  "name_prefix": "x264_x264",
  "codec_name": "libx264",
  "options": "",
  "crf": 23,
  "preset": "${RESULT_JSON}",
  "basefile": "/dist/base.mp4",
  "evaluation_file": "/dist/x264_x264_crf23_medium.mp4",
  "evaluation_size": 20000,
  "evaluation_encodetime": 100,
  "evaluation_vamf": 100,
  "evaluation_ssmi": 1
}]
EOF
)

jq '. |= .+[{"name_prefix": "${__result_row}"}]' > "${RESULT_JSON}"

jq \'". |= ${__result_row}"\' > "${RESULT_JSON}"
