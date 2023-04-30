#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""entrypoint."""
# Standard Library
import argparse
import copy
import json
import time
from time import gmtime
from time import strftime
from typing import Optional

# Third Party Library
from ffmpeg_progress_yield import FfmpegProgress
from tqdm import tqdm

parser = argparse.ArgumentParser(description="FFmpeg video quality encoding quality evaluation.")

parser.add_argument(
    "--config",
    help="config file path.",
    default="/source/encode_config.json",
)

parser.add_argument(
    "--dist",
    help="dist dir (default: /dist)",
    default="/dist",
)

parser.add_argument(
    "--encode",
    help="encode mode. (default: False)",
    action="store_true",
)

parser.add_argument("--ffmpeg-cattime")
args = parser.parse_args()


__config: dict = {
    "origfile": "/source/bbb_original.mp4",
    "basefile": "/dist/base.mp4",
    "crfs": [18],
    # "crfs": [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34],
    "hwaccel": [],
    "options": [],
    "presets": ["medium"],
    "codecs": [
        "libx264",
        "h264_nvenc",
        "h264_qsv",
        "h264_vaapi",
        "libx265",
        "h265_nvenc",
        "h265_qsv",
        "h265_vaapi",
    ],
}


def __getEncodeName(dist: str, codec: str, crf: int, preset: str, options: list) -> Optional[dict]:
    """Get encode name."""
    __options: list = copy.deepcopy(options)
    """x264"""
    if codec == "libx264":
        return {
            "filename": "{}/x264_x264_crf{}_{}".format(dist, crf, preset),
            "type": "x264",
            "hwaccel": [],
            "options": __options,
        }

    if codec == "h264_nvenc":
        return {
            "filename": "{}/x264_nvenc_crf{}_{}".format(dist, crf, preset),
            "type": "x264",
            "hwaccel": ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"],
            "options": __options,
        }

    if codec == "h264_qsv":
        return {
            "filename": "{}/x264_qsv_crf{}_{}".format(dist, crf, preset),
            "type": "x264",
            "hwaccel": ["-hwaccel", "qsv", "-hwaccel_output_format", "qsv"],
            "options": __options,
        }

    if codec == "h264_vaapi":
        return {
            "filename": "{}/x264_vaapi_crf{}_{}".format(dist, crf, preset),
            "type": "x264",
            "hwaccel": ["-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi"],
            "options": __options,
        }

    """x265"""
    if codec in ["libx265", "h265_nvenc", "h265_qsv", "h265_vaapi"]:
        __options.extend(["-tag:v", "hvc1"])

    if codec == "libx265":
        return {
            "filename": "{}/x265_x265_crf{}_{}".format(dist, crf, preset),
            "type": "x264",
            "hwaccel": [],
            "options": __options,
        }

    if codec == "h265_nvenc":
        return {
            "filename": "{}/x265_nvenc_crf{}_{}".format(dist, crf, preset),
            "type": "x264",
            "hwaccel": ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"],
            "options": __options,
        }

    if codec == "h265_qsv":
        return {
            "filename": "{}/x265_qsv_crf{}_{}".format(dist, crf, preset),
            "type": "x264",
            "hwaccel": ["-hwaccel", "qsv", "-hwaccel_output_format", "qsv"],
            "options": __options,
        }

    if codec == "h265_vaapi":
        return {
            "filename": "{}/x265_vaapi_crf{}_{}".format(dist, crf, preset),
            "type": "x264",
            "hwaccel": ["-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi"],
            "options": __options,
        }

    return None


def encoding(basefile: str, encode_cfg: dict) -> float:
    """Encode."""

    __ffmpege_time: list = [
        "ffmpeg",
        "-i",
        "{}".format(basefile),
        "-y",
        "{}.mp4".format(encode_cfg["filename"]),
        "-crf",
        "{}".format(encode_cfg["crf"]),
        "-preset",
        "{}".format(encode_cfg["preset"]),
        "-c:v",
        "{}".format(encode_cfg["codec"]),
        "-an",
    ]

    if encode_cfg["hwaccel"] != []:
        __ffmpege_time.extend(encode_cfg["hwaccel"])

    if encode_cfg["options"] != []:
        __ffmpege_time.extend(encode_cfg["options"])

    __start = time.time()
    __ff_encode = FfmpegProgress(__ffmpege_time)
    with tqdm(
        desc="[ENCODE] {}".format(encode_cfg["filename"]),
        total=100,
        position=1,
    ) as pbar:
        for progress in __ff_encode.run_command_with_progress():
            pbar.update(progress - pbar.n)
    elapsed_time = time.time() - __start

    print("\nelapsed_time: {}".format(strftime("%H:%M:%S", gmtime(elapsed_time))))
    return elapsed_time


def getvmaf(basefile: str, encode_cfg: dict) -> float:
    """Get VMAF."""

    __ffmpege_time: list = [
        "ffmpeg",
        "-i",
        "{}".format(basefile),
        "-i",
        "{}.mp4".format(encode_cfg["filename"]),
        "-lavfi",
        "libvmaf='model="
        + "version=vmaf_v0.6.1\\:name=vmaf:"
        + "feature=name=float_ssim:"
        + "n_threads=12:"
        + "log_fmt=json:log_path={}_vmaf.json".format(encode_cfg["filename"]),
        "-an",
        "-f",
        "null",
        "-",
    ]

    __start = time.time()
    __ff_vmaf = FfmpegProgress(__ffmpege_time)
    with tqdm(
        desc="[VMAF   ] {}".format(encode_cfg["filename"]),
    ) as pbar:
        for progress in __ff_vmaf.run_command_with_progress():
            pbar.update(progress - pbar.n)
    elapsed_time = time.time() - __start

    print("elapsed_time: {}".format(strftime("%H:%M:%S", gmtime(elapsed_time))))
    return elapsed_time


def main() -> None:
    """Main."""
    __origfile: str = __config["origfile"]
    __basefile: str = __config["basefile"]

    __results_list: list = []

    for __preset in __config["presets"]:
        for __crf in __config["crfs"]:
            for __codec in __config["codecs"]:
                __filename: Optional[dict] = __getEncodeName(
                    dist=args.dist,
                    codec=__codec,
                    crf=__crf,
                    preset=__preset,
                    options=__config["options"],
                )
                if __filename is None:
                    raise Exception("_filename error.")

                __result_template: dict = {
                    "type": __filename["type"],
                    "crf": __crf,
                    "preset": __preset,
                    "codec": __codec,
                    "elapsed": {
                        "encode": {
                            "second": 0,
                            "time": "",
                        },
                        "vmaf": {
                            "second": 0,
                            "time": "",
                        },
                    },
                    "vmaf": {},
                }
                __result_template.update(__filename)

                __results_list.append(__result_template)

        with open("{}/settings.json".format(args.dist), "w") as file:
            json.dump({"configs": __config, "encodes": __results_list}, file, indent=2)

    if args.encode is True:
        __ffmpege_time: list = [
            "ffmpeg",
            "-i",
            "{}".format(__origfile),
            "-y",
            "{}".format(__basefile),
            "-c:v",
            "copy",
            "-an",
        ]

        if args.ffmpeg_cattime is not None:
            __ffmpege_time.insert(1, "-t")
            __ffmpege_time.insert(2, "{}".format(args.ffmpeg_cattime))

        __start = time.time()
        __ff = FfmpegProgress(__ffmpege_time)
        with tqdm(
            desc="Create {} to {}".format(__origfile, __basefile),
            total=100,
            position=1,
        ) as pbar:
            for progress in __ff.run_command_with_progress():
                elapsed_time = time.time() - __start
                pbar.update(progress - pbar.n)

        print("\nelapsed_time:{:>10.2f} sec".format(elapsed_time))

        with open("{}/settings.json".format(args.dist), "rb") as fin:
            __encode_cfg = json.load(fin)

        __length: int = len(__encode_cfg["encodes"])
        for __index, __encode in enumerate(__encode_cfg["encodes"]):
            print(
                "=" * 80
                + "\n{:0>4}/{:0>4} ({:>7.2%})\n".format(__index, __length, __index / __length)
            )
            __encode_time = encoding(basefile=__basefile, encode_cfg=__encode)

            __results_list[__index]["elapsed"]["encode"]["second"] = __encode_time
            __results_list[__index]["elapsed"]["encode"]["time"] = strftime(
                "%H:%M:%S", gmtime(__encode_time)
            )

            __vmaf_time = getvmaf(basefile=__basefile, encode_cfg=__encode)
            __results_list[__index]["elapsed"]["vmaf"]["second"] = __vmaf_time
            __results_list[__index]["elapsed"]["vmaf"]["time"] = strftime(
                "%H:%M:%S", gmtime(__vmaf_time)
            )

            with open("{}_vmaf.json".format(__encode["filename"]), "rb") as file:
                __vmaf_log = json.load(file)
                __results_list[__index]["vmaf"] = {
                    "version": __vmaf_log["version"],
                    "pooled_metrics": {
                        "float_ssim": __vmaf_log["pooled_metrics"]["float_ssim"],
                        "vmaf": __vmaf_log["pooled_metrics"]["vmaf"],
                    },
                }

            with open("{}/settings.json".format(args.dist), "w") as file:
                json.dump({"configs": __config, "encodes": __results_list}, file, indent=2)


if __name__ == "__main__":
    main()
