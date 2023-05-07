#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""entrypoint."""
# Standard Library
import argparse
import glob
import hashlib
import json
import os
import time
from time import gmtime
from time import strftime
import os
import subprocess

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
    "-cy",
    "--conf-yes",
    help="Overwrite settings.json. (default: False)",
    action="store_true",
)

parser.add_argument(
    "--encode",
    help="encode mode. (default: False)",
    action="store_true",
)

parser.add_argument("--ffmpeg-cattime")
args = parser.parse_args()

__configs: dict = {
    "origfile": "/source/sample-ed-1080p.mp4",
    "basefile": "/dist/base.mp4",
    "patterns": [
        {
            "codec": "libx264",
            "type": "x264_crf21",
            "presets": ["veryfast", "medium", "veryslow"],
            "infile": {"options": []},
            "outfile": {"options": ["-crf", "21"]},
            "hwaccels": [],
        },
        {
            "codec": "libx264",
            "type": "x264_crf23",
            "presets": ["veryfast", "medium", "veryslow"],
            "infile": {"options": []},
            "outfile": {"options": ["-crf", "23"]},
            "hwaccels": [],
        },
        {
            "codec": "libx264",
            "type": "x264_crf25",
            "presets": ["veryfast", "medium", "veryslow"],
            "infile": {"options": []},
            "outfile": {"options": ["-crf", "25"]},
            "hwaccels": [],
        },
        {
            "codec": "h264_nvenc",
            "type": "x264",
            "presets": ["12", "15", "18"],
            "infile": {"options": []},
            "outfile": {"options": []},
            "hwaccels": ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"],
        },
        {
            "codec": "h264_qsv",
            "type": "x264",
            "presets": ["7", "4", "1"],
            "infile": {"options": []},
            "outfile": {"options": []},
            "hwaccels": ["-hwaccel", "qsv", "-hwaccel_output_format", "qsv"],
        },
        {
            "codec": "h264_vaapi",
            "type": "x264",
            "presets": [],
            "infile": {"options": []},
            "outfile": {"options": []},
            "hwaccels": ["-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi"],
        },
        {
            "codec": "libx265",
            "type": "x265_crf26",
            "presets": ["veryfast", "medium", "veryslow"],
            "infile": {"options": []},
            "outfile": {"options": ["-crf", "26", "-tag:v", "hvc1"]},
            "hwaccels": "",
        },
        {
            "codec": "libx265",
            "type": "x265_crf28",
            "presets": ["veryfast", "medium", "veryslow"],
            "infile": {"options": []},
            "outfile": {"options": ["-crf", "28", "-tag:v", "hvc1"]},
            "hwaccels": "",
        },
        {
            "codec": "libx265",
            "type": "x265_crf30",
            "presets": ["veryfast", "medium", "veryslow"],
            "infile": {"options": []},
            "outfile": {"options": ["-crf", "30", "-tag:v", "hvc1"]},
            "hwaccels": "",
        },
        {
            "codec": "hevc_nvenc",
            "type": "x265",
            "presets": ["12", "15", "18"],
            "infile": {"options": []},
            "outfile": {"options": ["-tag:v", "hvc1"]},
            "hwaccels": ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"],
        },
        {
            "codec": "hevc_qsv",
            "type": "x265",
            "presets": ["7", "4", "1"],
            "infile": {"options": []},
            "outfile": {"options": ["-tag:v", "hvc1"]},
            "hwaccels": ["-hwaccel", "qsv", "-hwaccel_output_format", "qsv"],
        },
        {
            "codec": "hevc_vaapi",
            "type": "x265",
            "presets": [],
            "infile": {"options": []},
            "outfile": {"options": ["-tag:v", "hvc1"]},
            "hwaccels": ["-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi"],
        },
    ],
}


def encoding(encode_cfg: dict, outputext: str) -> dict:
    """Encode."""

    __ffmpege_cmd: list = [
        "ffmpeg",
        "-y",
    ]

    if encode_cfg["hwaccels"] != []:
        __ffmpege_cmd.extend(encode_cfg["hwaccels"])

    if "infile" in encode_cfg:
        if encode_cfg["infile"]["options"] != []:
            __ffmpege_cmd.extend(encode_cfg["infile"]["options"])
        __ffmpege_cmd.append("-i")
        __ffmpege_cmd.append("{}".format(encode_cfg["infile"]["filename"]))

    if "outfile" in encode_cfg != []:
        if encode_cfg["outfile"]["options"] != []:
            __ffmpege_cmd.extend(encode_cfg["outfile"]["options"])
        __ffmpege_cmd.append("-c:v")
        __ffmpege_cmd.append("{}".format(encode_cfg["codec"]))

        if encode_cfg["preset"] != "none":
            __ffmpege_cmd.append("-preset")
            __ffmpege_cmd.append("{}".format(encode_cfg["preset"]))

        __ffmpege_cmd.append("{}{}".format(encode_cfg["outfile"]["filename"], outputext))

    print("__ffmpege_cmd: {}".format(__ffmpege_cmd))
    os.environ["FFREPORT"] = "file={}.log:level=32".format(encode_cfg["outfile"]["filename"])
    __start = time.time()
    __ff_encode = FfmpegProgress(__ffmpege_cmd)
    with tqdm(
        desc="[ENCODE] {}".format(encode_cfg["outfile"]["filename"]),
        total=100,
        position=1,
    ) as pbar:
        for progress in __ff_encode.run_command_with_progress():
            pbar.update(progress - pbar.n)
    os.environ.pop("FFREPORT", None)
    elapsed_time = time.time() - __start

    print("[PROBE ] {}".format(encode_cfg["outfile"]["filename"]))
    subprocess.run(
        args=[
            "ffprobe",
            "-v",
            "error",
            "-hide_banner",
            "-show_chapters",
            "-show_format",
            "-show_library_versions",
            "-show_program_version",
            "-show_programs",
            "-show_streams",
            "-print_format",
            "json",
            "-i",
            "{}{}".format(encode_cfg["outfile"]["filename"], outputext),
            "-o",
            "{}_ffprobe.json".format(encode_cfg["outfile"]["filename"]),
        ],
        timeout=10,
        check=True,
    )

    print("\nelapsed_time: {}".format(strftime("%H:%M:%S", gmtime(elapsed_time))))
    return {
        "commandline": __ffmpege_cmd,
        "elapsed_time": elapsed_time,
    }


def getvmaf(encode_cfg: dict, outputext: str) -> dict:
    """Get VMAF."""

    __ffmpege_cmd: list = [
        "ffmpeg",
        "-i",
        "{}".format(encode_cfg["infile"]["filename"]),
        "-i",
        "{}{}".format(encode_cfg["outfile"]["filename"], outputext),
        "-lavfi",
        "libvmaf='model="
        + "version=vmaf_v0.6.1\\:name=vmaf:"
        + "feature=name=float_ssim:"
        + "n_threads={}:".format(os.cpu_count())
        + "log_fmt=json:log_path={}_vmaf.json".format(encode_cfg["outfile"]["filename"]),
        "-an",
        "-f",
        "null",
        "-",
    ]

    __start = time.time()
    __ff_vmaf = FfmpegProgress(__ffmpege_cmd)
    with tqdm(
        desc="[VMAF   ] {}".format(encode_cfg["outfile"]["filename"]),
    ) as pbar:
        for progress in __ff_vmaf.run_command_with_progress():
            pbar.update(progress - pbar.n)
    elapsed_time = time.time() - __start

    print("elapsed_time: {}".format(strftime("%H:%M:%S", gmtime(elapsed_time))))
    return {
        "commandline": __ffmpege_cmd,
        "elapsed_time": elapsed_time,
    }


def main() -> None:
    """Main."""
    __origfile: str = __configs["origfile"]
    __basefile: str = __configs["basefile"]
    __baseext: str = os.path.splitext(__configs["basefile"])[-1]

    __results_list: list = []

    for __pattern in __configs["patterns"]:
        __presets: list = __pattern["presets"]
        if __presets == []:
            __presets.append("none")
        for __preset in __presets:
            __result_template: dict = {
                "codec": __pattern["codec"],
                "type": __pattern["type"],
                "preset": __preset,
                "infile": {
                    "filename": __basefile,
                    "options": __pattern["infile"]["options"],
                },
                "outfile": {
                    "filename": "{}/{}_{}_{}".format(
                        args.dist, __pattern["type"], __pattern["codec"], __preset
                    ),
                    "hash": "",
                    "size": 0,
                    "options": __pattern["outfile"]["options"],
                },
                "commandline": [],
                "hwaccels": __pattern["hwaccels"],
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
                "results": {
                    "compression": {
                        "ratio_persent": 0,
                        "speed": 0,
                    },
                    "vmaf": {},
                },
            }
            __results_list.append(__result_template)

    if not os.path.exists("{}/settings.json".format(args.dist)) or args.conf_yes is True:
        with open("{}/settings.json".format(args.dist), "w") as file:
            json.dump({"configs": __configs, "encodes": __results_list}, file, indent=2)

    if args.encode is True:
        __ffmpege_cmd: list = [
            "ffmpeg",
            "-y",
            "-i",
            "{}".format(__origfile),
            "-c:v",
            "copy",
            "-an",
            "{}".format(__basefile),
        ]

        if args.ffmpeg_cattime is not None:
            __ffmpege_cmd.insert(1, "-t")
            __ffmpege_cmd.insert(2, "{}".format(args.ffmpeg_cattime))

        __start = time.time()
        __ff = FfmpegProgress(__ffmpege_cmd)
        elapsed_time: float = 0
        with tqdm(
            desc="Create {} to {}".format(__origfile, __basefile),
            total=100,
            position=1,
        ) as pbar:
            for progress in __ff.run_command_with_progress():
                elapsed_time = time.time() - __start
                pbar.update(progress - pbar.n)

        print("\nelapsed_time:{:>10.2f} sec".format(elapsed_time))
        print("[PROBE ] {}".format(__basefile))
        subprocess.run(
            args=[
                "ffprobe",
                "-v",
                "error",
                "-hide_banner",
                "-show_chapters",
                "-show_format",
                "-show_library_versions",
                "-show_program_version",
                "-show_programs",
                "-show_streams",
                "-print_format",
                "json",
                "-i",
                "{}".format(__basefile),
                "-o",
                "{}".format(__basefile.replace(__baseext, "_ffprobe.json", 1)),
            ],
            timeout=10,
            check=True,
        )

        with open("{}".format(__basefile.replace(__baseext, "_ffprobe.json", 1)), "rb") as file:
            __base_probe_log = json.load(file)

        with open("{}/settings.json".format(args.dist), "rb") as fin:
            __encode_cfg = json.load(fin)

        __encode_cfg["configs"]["ffmpege"] = {
            "program_version": __base_probe_log["program_version"],
            "library_versions": __base_probe_log["library_versions"],
        }

        with open("{}/settings.json".format(args.dist), "w") as file:
            json.dump(
                {"configs": __encode_cfg["configs"], "encodes": __encode_cfg["encodes"]},
                file,
                indent=2,
            )

        files = glob.glob("{}/*{}".format(args.dist, __baseext))
        __dist_files: list = []
        for __dist_file in files:
            with open(__dist_file, "rb") as hash_file:
                __hasher = hashlib.sha256()
                __hasher.update(hash_file.read())
                __dist_files.append("{}".format(__hasher.hexdigest()))

        __length: int = len(__encode_cfg["encodes"])
        for __index, __encode in enumerate(__encode_cfg["encodes"]):
            print(
                "=" * 80
                + "\n{:0>4}/{:0>4} ({:>7.2%})\n".format(
                    (__index + 1), __length, (__index + 1) / __length
                )
            )

            __encode_exec_flg: bool = (
                __encode["outfile"]["hash"] == ""
                or __encode["outfile"]["hash"] not in __dist_files
            )
            print("outfile hash:  {}".format(__encode["outfile"]["hash"]))
            print("outfile cache: {}".format(not __encode_exec_flg))
            if __encode_exec_flg:
                __encode_rep = encoding(encode_cfg=__encode, outputext=__baseext)
                __encode_cfg["encodes"][__index]["commandline"] = __encode_rep["commandline"]

                with open(
                    "{}{}".format(__encode["outfile"]["filename"], __baseext), "rb"
                ) as file_hash_cncode:
                    __hasher = hashlib.sha256()
                    __hasher.update(file_hash_cncode.read())
                    __encode_cfg["encodes"][__index]["outfile"]["hash"] = "{}".format(
                        __hasher.hexdigest()
                    )

                __encode_cfg["encodes"][__index]["elapsed"]["encode"]["second"] = __encode_rep[
                    "elapsed_time"
                ]
                __encode_cfg["encodes"][__index]["elapsed"]["encode"]["time"] = strftime(
                    "%H:%M:%S", gmtime(__encode_rep["elapsed_time"])
                )

                """compression"""
                with open("{}_ffprobe.json".format(__encode["outfile"]["filename"]), "rb") as file:
                    __probe_log = json.load(file)

                    """infile"""
                    __encode_cfg["encodes"][__index]["infile"]["duration"] = float(
                        __base_probe_log["format"]["duration"]
                    )
                    __encode_cfg["encodes"][__index]["infile"]["size"] = int(
                        __base_probe_log["format"]["size"]
                    )

                    """outfile"""
                    __encode_cfg["encodes"][__index]["outfile"]["duration"] = float(
                        __probe_log["format"]["duration"]
                    )
                    __encode_cfg["encodes"][__index]["outfile"]["size"] = int(
                        __probe_log["format"]["size"]
                    )

                    """results"""
                    __encode_cfg["encodes"][__index]["results"]["compression"][
                        "ratio_persent"
                    ] = 1 - (
                        float(__probe_log["format"]["size"])
                        / float(__base_probe_log["format"]["size"])
                    )
                    __encode_cfg["encodes"][__index]["results"]["compression"]["speed"] = (
                        float(__probe_log["format"]["duration"]) / __encode_rep["elapsed_time"]
                    )

                with open("{}/settings.json".format(args.dist), "w") as file:
                    json.dump(
                        {"configs": __encode_cfg["configs"], "encodes": __encode_cfg["encodes"]},
                        file,
                        indent=2,
                    )

                """VMAF"""
                __vmaf_rsp = getvmaf(encode_cfg=__encode, outputext=__baseext)
                __encode_cfg["encodes"][__index]["elapsed"]["vmaf"]["second"] = __vmaf_rsp[
                    "elapsed_time"
                ]
                __encode_cfg["encodes"][__index]["elapsed"]["vmaf"]["time"] = strftime(
                    "%H:%M:%S", gmtime(__vmaf_rsp["elapsed_time"])
                )

                with open("{}_vmaf.json".format(__encode["outfile"]["filename"]), "rb") as file:
                    __vmaf_log = json.load(file)
                    __encode_cfg["encodes"][__index]["results"]["vmaf"] = {
                        "version": __vmaf_log["version"],
                        "commandline": __vmaf_rsp["commandline"],
                        "pooled_metrics": {
                            "float_ssim": __vmaf_log["pooled_metrics"]["float_ssim"],
                            "vmaf": __vmaf_log["pooled_metrics"]["vmaf"],
                        },
                    }

            with open("{}/settings.json".format(args.dist), "w") as file:
                json.dump(
                    {"configs": __encode_cfg["configs"], "encodes": __encode_cfg["encodes"]},
                    file,
                    indent=2,
                )


if __name__ == "__main__":
    main()

# %%
""
