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
    default="./videos/source/settings.json",
)

parser.add_argument(
    "--dist",
    help="dist dir (default: /dist)",
    default="./videos/dist",
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
parser.add_argument(
    "-fthreads",
    "--ffmpeg-threads",
    help="Set the number of threads to be used (default: 4)",
    type=int,
    default=4,
)
args = parser.parse_args()


def encoding(encode_cfg: dict, outputext: str) -> dict:
    """Encode."""
    __ffmpege_cmd: list = [
        "ffmpeg",
        "-y",
        "-threads",
        f"{args.ffmpeg_threads}",
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
            __ffmpege_cmd.append("-preset:v")
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
        f"{encode_cfg['outfile']['filename']}{outputext}",
        "-i",
        f"{encode_cfg['infile']['filename']}",
        "-lavfi",
        (
            "[0:v]settb=AVTB,setpts=PTS-STARTPTS[Distorted];"
            "[1:v]settb=AVTB,setpts=PTS-STARTPTS[Reference];"
            "[Distorted][Reference]libvmaf=eof_action=endall:"
            "log_fmt=json:"
            f"log_fmt=json:log_path={encode_cfg['outfile']['filename']}_vmaf.json:"
            f"n_threads={os.cpu_count()}:"
            "pool=harmonic_mean:"
            "feature=name=psnr|name=float_ssim:"
            "model=version=vmaf_v0.6.1"
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
        total=100,
        position=1,
    ) as pbar:
        for progress in __ff_vmaf.run_command_with_progress():
            pbar.update(progress - pbar.n)
    elapsed_time = time.time() - __start

    print(f"elapsed_time: {strftime('%H:%M:%S', gmtime(elapsed_time))}")  # noqa: T201
    return {
        "commandline": __ffmpege_cmd,
        "elapsed_time": elapsed_time,
    }


def main() -> None:  # noqa: PLR0915
    """Main."""
    __configs: dict = load_config(configfile=args.config)
    __origfile: str = __configs["configs"]["origfile"]
    __basefile: str = __configs["configs"]["basefile"]
    __basehash: str = __configs["configs"]["basehash"]
    __baseext: str = Path(__basefile).suffix

    if args.encode is True:
        if __basehash == "":
            __ffmpege_cmd: list = [
                "ffmpeg",
                "-y",
                "-threads",
                f"{args.ffmpeg_threads}",
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

            with Path(f"{args.config}").open("r") as file:
                __encode_cfg = json.load(file)

            with Path(f"{__basefile}").open("rb") as file:
                __hasher = hashlib.sha256()
                __hasher.update(file.read())
                __encode_cfg["configs"]["basehash"] = f"{__hasher.hexdigest()}"

            __encode_cfg["configs"]["ffmpege"] = {
                "program_version": __base_probe_log["program_version"],
                "library_versions": __base_probe_log["library_versions"],
            }

            with Path(f"{args.config}").open("w") as file:
                json.dump(
                    {"configs": __encode_cfg["configs"], "encodes": __encode_cfg["encodes"]},
                    file,
                    indent=2,
                )
        else:
            print("base to skip encode")  # noqa: T201

        with Path(f"{args.config}").open("r") as file:
            __encode_cfg = json.load(file)

        files = Path(args.dist).glob(f"*{__baseext}")
        __dist_files: list = []
        for __dist_file in files:
            with Path(__dist_file).open("rb") as file:
                __hasher = hashlib.sha256()
                __hasher.update(file.read())
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
                    __encode_cfg["encodes"][__index]["outfile"]["bit_rate_kbs"] = float(
                        (int(__probe_log["format"]["bit_rate"]) / 1024),
                    )
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

                with Path(f"{args.config}").open("w") as file:
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

            with Path(f"{args.config}").open("w") as file:
                json.dump(
                    {"configs": __encode_cfg["configs"], "encodes": __encode_cfg["encodes"]},
                    file,
                    indent=2,
                )


def load_config(configfile: str) -> dict:
    """Main."""
    __configs: dict = {}

    "configfile ディレクトリが存在しない場合は作成"
    if not Path(configfile).parent.exists():
        Path.mkdir(Path(configfile).parent, parents=True)

    "settings.json があるか確認"
    if Path(f"{configfile}").exists():
        print(f"{configfile} file found.")  # noqa: T201
        with Path(f"{configfile}").open("r") as file:
            __configs = json.load(file)
    else:
        __configs = {
            "configs": {
                "origfile": "./videos/source/BBB_JapanTV_MPEG-2_1920x1080_30p.m2ts",
                "basefile": "./videos/dist/base.mkv",
                "basehash": "",
                "patterns": [
                    {
                        "codec": "libx264",
                        "type": "libx264",
                        "comments": "",
                        "presets": ["medium"],
                        "infile": {"options": []},
                        "outfile": {
                            "options": [
                                ["-crf", "23"],
                            ],
                        },
                        "hwaccels": [],
                    },
                ],
            },
            "encodes": [],
        }

    __origfile: str = __configs["configs"]["origfile"]
    __basefile: str = __configs["configs"]["basefile"]
    __results_list: list = []
    __existing_encodes = {encode["id"]: encode for encode in __configs.get("encodes", [])}
    __results_list.extend(__configs.get("encodes", []))

    for __pattern in __configs["configs"]["patterns"]:
        __presets: list = __pattern["presets"]
        if __presets == []:
            __presets.append("none")
        for __preset in __presets:
            for __out_option in __pattern["outfile"]["options"]:
                __codec: str = __pattern["codec"]
                __type: str = __pattern["type"]
                __comments: str = __pattern["comments"]
                __threads: str = args.ffmpeg_threads
                __infile_opts: list = __pattern["infile"]["options"]
                __hwaccels: list = __pattern["hwaccels"]
                __out_option_hash: str = hashlib.sha256(
                    str(
                        [
                            f"{__origfile}{__type}{__codec}{__preset}{__out_option}",
                            f"{__basefile}{__threads}{__hwaccels}{__infile_opts}",
                        ],
                    ).encode(),
                ).hexdigest()
                __result_template: dict = {
                    "id": f"{__out_option_hash}",
                    "codec": __codec,
                    "type": __type,
                    "comments": __comments,
                    "preset": __preset,
                    "threads": __threads,
                    "infile": {
                        "filename": __basefile,
                        "options": __infile_opts,
                    },
                    "outfile": {
                        "filename": f"{args.dist}/{__type}_{__codec}_{__preset}_{__out_option_hash[:12]}",
                        "bit_rate": 0.0,
                        "duration": 0.0,
                        "hash": "",
                        "options": __out_option,
                        "size": 0,
                    },
                    "commandline": [],
                    "hwaccels": __hwaccels,
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

                # 既存の encodes と比較して削除または追加
                if __result_template["id"] not in __existing_encodes:
                    __results_list.append(__result_template)
                    print(  # noqa: T201
                        f"encode new ... {
                            (
                                __result_template['codec'],
                                __result_template['type'],
                                __result_template['outfile']['options'],
                            )
                        }",
                    )

    with Path(f"{configfile}").open("w") as file:
        __configs["encodes"] = __results_list
        json.dump(__configs, file, indent=2)

    return __configs


if __name__ == "__main__":
    main()
    # print(load_config(configfile=args.config))

# %%
""
