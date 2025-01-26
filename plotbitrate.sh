#!/usr/bin/env bash
set -eu

__DIR="./videos"
__array="$(find "${__DIR}/source" "${__DIR}/dist" -maxdepth 1 -name '*.mp4' -or -name '*.ts' -or -name '*.mkv' -or -name '*.m2ts')"
__array_length=$(find "${__DIR}/source" "${__DIR}/dist" -maxdepth 1 -name '*.mp4' -or -name '*.ts' -or -name '*.mkv' -or -name '*.m2ts' | wc -l)


function plot {
  __index=0
  for __file in $__array
  do
    __suffix="${__file##*.}"
    __filename="$(basename "${__file}" ".${__suffix}")"
    __index=$(( $__index + 1))
    echo -e "\t$__index/$__array_length\t${__file}"

    if [ "$(ffprobe -v error -hide_banner -show_streams ${__file} | grep -c -e 'codec_type=video')" != 0 ]; then
      set -x
      poetry run plotbitrate --show-frame-types --stream video --format "csv_raw" --output "${__DIR}/dist/${__filename}_video.csv" "${__file}"
      poetry run plotbitrate --show-frame-types --stream video                    --output "${__DIR}/dist/${__filename}_video.svg" "${__file}"
      set +x
    fi

    if [ "$(ffprobe -v error -hide_banner -show_streams ${__file} | grep -c -e 'codec_type=audio')" != 0 ]; then
      set -x
      poetry run plotbitrate --show-frame-types --stream audio --format "csv_raw" --output "${__DIR}/dist/${__filename}_audio.csv" "${__file}"
      poetry run plotbitrate --show-frame-types --stream audio                    --output "${__DIR}/dist/${__filename}_audio.svg" "${__file}"
      set +x
    fi
    echo -e "\n\n"
  done

}

function csv {
  jq -r '
    [
      "codec",                                "type",                                          "preset",
      "threads",                              "outfile_size_byte",                             "bit_rate_kbs",
      "outfile_options",                      "elapsed_encode_second",                         "elapsed_encode_time",
      "compression_ratio_persent",            "compression_speed",                             "ssim_mean",
      "ssim_harmonic_mean",                                                                    "vmaf_mean",
      "vmaf_harmonic_mean"
    ],
    (.encodes[] |
    [
      .codec,                                 .type,                                           .preset,
      .threads,                               .outfile.size,                                   .outfile.bit_rate_kbs,
      (.outfile.options | join(" ")),         .elapsed.encode.second,                          .elapsed.encode.time,
      .results.compression.ratio_persent,     .results.compression.speed,                      .results.vmaf.pooled_metrics.float_ssim.mean,
      .results.vmaf.pooled_metrics.float_ssim.harmonic_mean,                                   .results.vmaf.pooled_metrics.vmaf.mean,
      .results.vmaf.pooled_metrics.vmaf.harmonic_mean
    ]) |
    @csv
  ' "${__DIR}/dist/settings.json" > "${__DIR}/dist/summary.csv"
  echo "output ${__DIR}/dist/summary.csv"
}

if [ $# -eq 0 ]; then
  # 引数がない場合
  plot
  csv
else
  # 引数がある場合
  case "${1}" in
    plot)
      "${1}"
      ;;
    csv)
      "${1}"
      ;;
    *)
      echo "Invalid argument. Usage: \$0 [plot|csv]"
      ;;
  esac
fi
