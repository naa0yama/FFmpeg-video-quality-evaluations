#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""entrypoint."""

# Standard Library
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from time import gmtime
from time import strftime

from ffmpeg_progress_yield import FfmpegProgress
from tqdm import tqdm

parser = argparse.ArgumentParser(description="FFmpeg video quality encoding quality evaluation.")

parser.add_argument(
    "--config",
    help="config file path.",
    default="./videos/source/encode_config.json",
)

parser.add_argument(
    "--dist",
    help="dist dir (default: /dist)",
    default="./videos/dist",
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

parser.add_argument(
    "-fss",
    "--ffmpeg-starttime",
    help="-ss <time_off>  start transcoding at specified time (default: None)",
)
parser.add_argument(
    "-ft",
    "--ffmpeg-cattime",
    help="-t <duration>  stop transcoding after specified duration (default: None)",
)
args = parser.parse_args()

__configs: dict = {
    "origfile": "./videos/source/BBB_JapanTV_MPEG-2_1440x1080_30i.m2ts",
    "basefile": "./videos/dist/base.mkv",
    "patterns": [
        {
            "codec": "libx264",
            "type": "libx264",
            "presets": ["medium"],
            "infile": {"options": []},
            "outfile": {"options": []},
            "hwaccels": [],
        },
        {
            "codec": "av1_qsv",
            "type": "av1",
            "presets": ["veryfast", "medium", "veryslow"],
            "infile": {"options": []},
            "outfile": {"options": []},
            "hwaccels": ["-hwaccel", "qsv", "-hwaccel_output_format", "qsv"],
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

    print(f"__ffmpege_cmd: {__ffmpege_cmd}")  # noqa: T201
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

    print(f"[PROBE ] {encode_cfg['outfile']['filename']}")  # noqa: T201
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

    print(f"\nelapsed_time: {strftime('%H:%M:%S', gmtime(elapsed_time))}")  # noqa: T201
    return {
        "commandline": __ffmpege_cmd,
        "elapsed_time": elapsed_time,
    }


def getvmaf(encode_cfg: dict, outputext: str) -> dict:
    """Get VMAF."""
    __ffmpege_cmd: list = [
        "ffmpeg",
        "-i",
        f"{encode_cfg['infile']['filename']}",
        "-i",
        f"{encode_cfg['outfile']['filename']}{outputext}",
        "-filter_complex",
        (
            "[0:v][1:v]libvmaf=model=version=vmaf_v0.6.1\\:pool=harmonic_mean:feature=name=psnr|name=float_ssim:"
            f"n_threads={os.cpu_count()}:"
            f"log_fmt=json:log_path={encode_cfg['outfile']['filename']}_vmaf.json"
        ),
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

    print(f"elapsed_time: {strftime('%H:%M:%S', gmtime(elapsed_time))}")  # noqa: T201
    return {
        "commandline": __ffmpege_cmd,
        "elapsed_time": elapsed_time,
    }


def main() -> None:  # noqa: PLR0915, C901
    """Main."""
    __origfile: str = __configs["origfile"]
    __basefile: str = __configs["basefile"]
    __baseext: str = Path(__configs["basefile"]).suffix

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
                    "filename": f"{args.dist}/{__pattern['type']}_{__pattern['codec']}_{__preset}",
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

    if not Path(f"{args.dist}/settings.json").exists() or args.conf_yes is True:
        with Path(f"{args.dist}/settings.json").open("w") as file:
            json.dump({"configs": __configs, "encodes": __results_list}, file, indent=2)

    if args.encode is True:
        __ffmpege_cmd: list = [
            "ffmpeg",
            "-y",
            "-i",
            f"{__origfile}",
            "-c:v",
            "copy",
            "-an",
            f"{__basefile}",
        ]

        if args.ffmpeg_cattime is not None:
            __ffmpege_cmd.insert(1, "-t")
            __ffmpege_cmd.insert(2, f"{args.ffmpeg_cattime}")

        if args.ffmpeg_starttime is not None:
            __ffmpege_cmd.insert(1, "-ss")
            __ffmpege_cmd.insert(2, f"{args.ffmpeg_starttime}")

        __start = time.time()
        __ff = FfmpegProgress(__ffmpege_cmd)
        elapsed_time: float = 0
        with tqdm(
            desc=f"Create {__origfile} to {__basefile}",
            total=100,
            position=1,
        ) as pbar:
            for progress in __ff.run_command_with_progress():
                elapsed_time = time.time() - __start
                pbar.update(progress - pbar.n)

        print(f"\nelapsed_time:{elapsed_time:>10.2f} sec")  # noqa: T201
        print(f"[PROBE ] {__basefile}")  # noqa: T201
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
                f"{__basefile}",
                "-o",
                f"{__basefile.replace(__baseext, '_ffprobe.json', 1)}",
            ],
            timeout=10,
            check=True,
        )

        with Path(f"{__basefile.replace(__baseext, '_ffprobe.json', 1)}").open("r") as file:
            __base_probe_log = json.load(file)

        with Path(f"{args.dist}/settings.json").open("r") as fin:
            __encode_cfg = json.load(fin)

        __encode_cfg["configs"]["ffmpege"] = {
            "program_version": __base_probe_log["program_version"],
            "library_versions": __base_probe_log["library_versions"],
        }

        with Path(f"{args.dist}/settings.json").open("w") as file:
            json.dump(
                {"configs": __encode_cfg["configs"], "encodes": __encode_cfg["encodes"]},
                file,
                indent=2,
            )

        files = Path(args.dist).glob(f"*{__baseext}")
        __dist_files: list = []
        for __dist_file in files:
            with Path(__dist_file).open("rb") as hash_file:
                __hasher = hashlib.sha256()
                __hasher.update(hash_file.read())
                __dist_files.append(f"{__hasher.hexdigest()}")

        __length: int = len(__encode_cfg["encodes"])
        for __index, __encode in enumerate(__encode_cfg["encodes"]):
            print(  # noqa: T201
                "=" * 80
                + f"\n{__index + 1:0>4}/{__length:0>4} ({(__index + 1) / __length:>7.2%})\n",
            )

            __encode_exec_flg: bool = (
                __encode["outfile"]["hash"] == ""
                or __encode["outfile"]["hash"] not in __dist_files
            )
            print(f"outfile hash:  {__encode['outfile']['hash']}")  # noqa: T201
            print(f"outfile cache: {not __encode_exec_flg}")  # noqa: T201
            if __encode_exec_flg:
                __encode_rep = encoding(encode_cfg=__encode, outputext=__baseext)
                __encode_cfg["encodes"][__index]["commandline"] = __encode_rep["commandline"]

                with Path(f"{__encode['outfile']['filename']}{__baseext}").open(
                    "rb",
                ) as file_hash_cncode:
                    __hasher = hashlib.sha256()
                    __hasher.update(file_hash_cncode.read())
                    __encode_cfg["encodes"][__index]["outfile"]["hash"] = f"{__hasher.hexdigest()}"

                __encode_cfg["encodes"][__index]["elapsed"]["encode"]["second"] = __encode_rep[
                    "elapsed_time"
                ]
                __encode_cfg["encodes"][__index]["elapsed"]["encode"]["time"] = strftime(
                    "%H:%M:%S",
                    gmtime(__encode_rep["elapsed_time"]),
                )

                """compression"""
                with Path(f"{__encode['outfile']['filename']}_ffprobe.json").open("r") as file:
                    __probe_log = json.load(file)

                    """infile"""
                    __encode_cfg["encodes"][__index]["infile"]["duration"] = float(
                        __base_probe_log["format"]["duration"],
                    )
                    __encode_cfg["encodes"][__index]["infile"]["size"] = int(
                        __base_probe_log["format"]["size"],
                    )

                    """outfile"""
                    __encode_cfg["encodes"][__index]["outfile"]["duration"] = float(
                        __probe_log["format"]["duration"],
                    )
                    __encode_cfg["encodes"][__index]["outfile"]["size"] = int(
                        __probe_log["format"]["size"],
                    )

                    """results"""
                    __encode_cfg["encodes"][__index]["results"]["compression"]["ratio_persent"] = (
                        1
                        - (
                            float(__probe_log["format"]["size"])
                            / float(__base_probe_log["format"]["size"])
                        )
                    )
                    __encode_cfg["encodes"][__index]["results"]["compression"]["speed"] = (
                        float(__probe_log["format"]["duration"]) / __encode_rep["elapsed_time"]
                    )

                with Path(f"{args.dist}/settings.json").open("w") as file:
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
                    "%H:%M:%S",
                    gmtime(__vmaf_rsp["elapsed_time"]),
                )

                with Path(f"{__encode['outfile']['filename']}_vmaf.json").open("r") as file:
                    __vmaf_log = json.load(file)
                    __encode_cfg["encodes"][__index]["results"]["vmaf"] = {
                        "version": __vmaf_log["version"],
                        "commandline": __vmaf_rsp["commandline"],
                        "pooled_metrics": {
                            "float_ssim": __vmaf_log["pooled_metrics"]["float_ssim"],
                            "vmaf": __vmaf_log["pooled_metrics"]["vmaf"],
                        },
                    }

            with Path(f"{args.dist}/settings.json").open("w") as file:
                json.dump(
                    {"configs": __encode_cfg["configs"], "encodes": __encode_cfg["encodes"]},
                    file,
                    indent=2,
                )


if __name__ == "__main__":
    main()

# %%
""
