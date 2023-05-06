set -eu

PLOTBITRATE_DIR="/usr/local/lib/python${PYTHON_VERSION:0:4}/site-packages"
FILE="${1}"
OUTPUTDIR="/dist"
SUFFIX="${2:-.mp4}"
FILENAME="$(basename "${FILE}" "${SUFFIX}")"

cd "${PLOTBITRATE_DIR}"

if [ "$(ffprobe -v error -hide_banner -show_streams ${FILE} | grep -c -e 'codec_type=video')" != 0 ]; then
  set -x
  python plotbitrate.py --show-frame-types --stream video --format "csv_raw" --output "${OUTPUTDIR}/${FILENAME}_video.csv" "${FILE}"
  python plotbitrate.py --show-frame-types --stream video                    --output "${OUTPUTDIR}/${FILENAME}_video.svg" "${FILE}"
  set +x
fi

if [ "$(ffprobe -v error -hide_banner -show_streams ${FILE} | grep -c -e 'codec_type=audio')" != 0 ]; then
  set -x
  python plotbitrate.py --show-frame-types --stream audio --format "csv_raw" --output "${OUTPUTDIR}/${FILENAME}_audio.csv" "${FILE}"
  python plotbitrate.py --show-frame-types --stream audio                    --output "${OUTPUTDIR}/${FILENAME}_audio.svg" "${FILE}"
  set +x
fi
