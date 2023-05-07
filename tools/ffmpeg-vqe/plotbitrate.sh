set -eu

OUTPUTDIR="/dist"

__array="$(find /source /dist -name '*.mp4' -or -name '*.ts' -or -name '*.mkv')"
__array_length=$(find /source /dist -name '*.mp4' -or -name '*.ts' -or -name '*.mkv' | wc -l)

__index=0
for __file in $__array
do
  __suffix="${__file##*.}"
  __filename="$(basename "${__file}" ".${__suffix}")"
  __index=$(( $__index + 1))
  echo -e "\t$__index/$__array_length\t${__file}"

  if [ "$(ffprobe -v error -hide_banner -show_streams ${__file} | grep -c -e 'codec_type=video')" != 0 ]; then
    set -x
    plotbitrate --show-frame-types --stream video --format "csv_raw" --output "${OUTPUTDIR}/${__filename}_video.csv" "${__file}"
    plotbitrate --show-frame-types --stream video                    --output "${OUTPUTDIR}/${__filename}_video.svg" "${__file}"
    set +x
  fi

  if [ "$(ffprobe -v error -hide_banner -show_streams ${__file} | grep -c -e 'codec_type=audio')" != 0 ]; then
    set -x
    plotbitrate --show-frame-types --stream audio --format "csv_raw" --output "${OUTPUTDIR}/${__filename}_audio.csv" "${__file}"
    plotbitrate --show-frame-types --stream audio                    --output "${OUTPUTDIR}/${__filename}_audio.svg" "${__file}"
    set +x
  fi
  echo -e "\n\n"
done
