#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""entrypoint."""

# Standard Library
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from time import gmtime
from time import strftime
from typing import Any

from ffmpeg_progress_yield import FfmpegProgress
import ruamel.yaml
from tqdm import tqdm


class NoAliasDumper(ruamel.yaml.representer.RoundTripRepresenter):
    """ruamel.yaml custom class."""

    def ignore_aliases(self, data: Any) -> bool:  # noqa: ARG002, ANN401
        """Disabled alias."""
        return True


class VQEError(Exception):
    """VQE Error class."""

    def __init__(self, message: str) -> None:
        """Init."""
        super().__init__(f"Error: {message}")


yaml = ruamel.yaml.YAML(typ="safe", pure=True)
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.default_flow_style = False
yaml.explicit_start = True
yaml.width = 200
yaml.Representer = NoAliasDumper
parser = argparse.ArgumentParser(description="FFmpeg video quality encoding quality evaluation.")

parser.add_argument(
    "--config",
    help="config file path.",
    default="./videos/source/settings.yml",
)

parser.add_argument(
    "--dist",
    help="dist dir (default: ./videos/dist)",
    default="./videos/dist",
)

parser.add_argument(
    "-cy",
    "--config-overwrite",
    help="Overriding config with defaults. (default: False)",
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
parser.add_argument(
    "-fthreads",
    "--ffmpeg-threads",
    help="Set the number of threads to be used (default: 4)",
    type=int,
    default=4,
)
args = parser.parse_args()


def getframeinfo(filename: str) -> dict:
    """Get frame Information."""
    __probe_log: dict = {}
    __stream: dict = {"gop": 0, "has_b_frames": 0, "refs": 0, "frames": {"I": 0, "P": 0, "B": 0}}
    # フレームのカウントを初期化
    __gop_lengths = []
    __current_gop_length = 0
    __first_gop_length = 0

    with Path(f"{filename}").open("r") as file:
        __probe_log = json.load(file)

    # フレーム情報をループしてカウント
    for frame in __probe_log["frames"]:
        frame_type = frame["pict_type"]
        if frame_type in __stream["frames"]:
            __stream["frames"][frame_type] += 1

        # Iフレームが見つかったらGOPの長さを記録
        if frame_type == "I":
            if __current_gop_length > 0:
                __gop_lengths.append(__current_gop_length)
                if __first_gop_length == 0:
                    __first_gop_length = __current_gop_length
            __current_gop_length = 1  # Iフレーム自体をカウント
        else:
            __current_gop_length += 1

    # 最後のGOPの長さを追加
    if __current_gop_length > 0:
        __gop_lengths.append(__current_gop_length)
        if __first_gop_length == 0:
            __first_gop_length = __current_gop_length

    __stream["gop"] = int(__first_gop_length)
    __stream["has_b_frames"] = int(__probe_log["streams"][0]["has_b_frames"])
    __stream["refs"] = int(__probe_log["streams"][0]["refs"])

    """ "frames" を削除"""
    if "frames" in __probe_log:
        del __probe_log["frames"]

    with Path(f"{filename}").open("w") as file:
        json.dump(__probe_log, file, indent=2)

    return __stream


def encoding(encode_cfg: dict, outputext: str, probe_timeout: int) -> dict:  # noqa: C901
    """Encode."""
    __ffmpege_cmd: list = [
        "ffmpeg",
        "-y",
        "-threads",
        f"{args.ffmpeg_threads}",
    ]

    if encode_cfg["hwaccels"] != "":
        __ffmpege_cmd.extend(str(encode_cfg["hwaccels"]).split())

    if "infile" in encode_cfg:
        if encode_cfg["infile"]["option"] != "":
            __ffmpege_cmd.extend(str(encode_cfg["infile"]["option"]).split())
        __ffmpege_cmd.append("-i")
        __ffmpege_cmd.append(f"{encode_cfg['infile']['filename']}")

    if "outfile" in encode_cfg != []:
        if encode_cfg["outfile"]["options"] != []:
            __ffmpege_cmd.extend(str(encode_cfg["outfile"]["options"]).split())
        __ffmpege_cmd.append("-c:v")
        __ffmpege_cmd.append(f"{encode_cfg['codec']}")

        if encode_cfg["preset"] != "none":
            __ffmpege_cmd.append("-preset:v")
            __ffmpege_cmd.append(f"{encode_cfg['preset']}")

        __ffmpege_cmd.append(f"{encode_cfg['outfile']['filename']}{outputext}")

    print(f"__ffmpege_cmd: {__ffmpege_cmd}")  # noqa: T201
    os.environ["FFREPORT"] = f"file={encode_cfg['outfile']['filename']}.log:level=32"
    __start = time.time()
    __ff_encode = FfmpegProgress(__ffmpege_cmd)
    with tqdm(
        desc=f"[ENCODE] {encode_cfg['outfile']['filename']}",
        total=100,
        position=1,
    ) as pbar:
        for progress in __ff_encode.run_command_with_progress():
            pbar.update(progress - pbar.n)
    os.environ.pop("FFREPORT", None)
    elapsed_time = time.time() - __start
    print(f"\nelapsed_time: {strftime('%H:%M:%S', gmtime(elapsed_time))}")  # noqa: T201

    __probe_filename: str = f"{encode_cfg['outfile']['filename']}_ffprobe.json"
    __proble_cmd: list = [
        "ffprobe",
        "-v",
        "error",
        "-hide_banner",
        "-show_streams",
        "-show_format",
        "-show_frames",
        "-print_format",
        "json",
        "-i",
        f"{encode_cfg['outfile']['filename']}{outputext}",
        "-o",
        __probe_filename,
    ]
    process = subprocess.Popen(
        args=__proble_cmd,
    )
    for _timeout in tqdm(range(probe_timeout), desc=f"[PROBE ] {__probe_filename}", unit="s"):
        time.sleep(1)
        if process.poll() is not None:
            break
    if process.poll() is None:
        process.terminate()
        raise subprocess.TimeoutExpired(__proble_cmd, probe_timeout)

    return {
        "commandline": " ".join(__ffmpege_cmd),
        "elapsed_time": elapsed_time,
        "stream": getframeinfo(f"{__probe_filename}"),
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
        desc=f"[VMAF  ] {encode_cfg['outfile']['filename']}",
        total=100,
        position=1,
    ) as pbar:
        for progress in __ff_vmaf.run_command_with_progress():
            pbar.update(progress - pbar.n)
    elapsed_time = time.time() - __start

    print(f"elapsed_time: {strftime('%H:%M:%S', gmtime(elapsed_time))}")  # noqa: T201
    return {
        "commandline": " ".join(__ffmpege_cmd),
        "elapsed_time": elapsed_time,
    }


def load_config(configfile: str) -> dict:
    """Load config."""
    __configs: dict = {}

    "configfile ディレクトリが存在しない場合は作成"
    if not Path(configfile).parent.exists():
        Path.mkdir(Path(configfile).parent, parents=True)

    "settings.json があるか、 --config-overwite が付いている"
    if Path(f"{configfile}").exists() and not args.config_overwrite:
        print(f"{configfile} file found.")  # noqa: T201
        with Path(f"{configfile}").open("r") as file:
            __configs = yaml.load(file)
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
                        "infile": {"option": ""},
                        "outfile": {
                            "options": [
                                "-crf 23",
                                "-crf 28",
                            ],
                        },
                        "hwaccels": "",
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
            if type(__pattern["outfile"]["options"]) is not list:
                __msg: str = (
                    f"outfile.options is must list[str] : {__pattern['outfile']['options']}"
                )
                raise VQEError(__msg)
            for __out_option in __pattern["outfile"]["options"]:
                __codec: str = __pattern["codec"]
                __type: str = __pattern["type"]
                __comments: str = __pattern["comments"]
                __threads: str = args.ffmpeg_threads
                __infile_opts: str = __pattern["infile"]["option"]
                __hwaccels: str = __pattern["hwaccels"]
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
                        "option": __infile_opts,
                    },
                    "outfile": {
                        "filename": f"{args.dist}/{__type}_{__codec}_{__preset}_{__out_option_hash[:12]}",
                        "bit_rate_kbs": 0.0,
                        "duration": 0.0,
                        "hash": "",
                        "options": __out_option,
                        "size_kbyte": 0,
                    },
                    "commandline": "",
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

    print(f"\n\n {len(__results_list)} pattern generate.\n\n")  # noqa: T201
    with Path(f"{configfile}").open("w") as file:
        __configs["encodes"] = __results_list
        yaml.dump(__configs, file)

    return __configs


def getcsv(configfile: str) -> None:
    """Get csv."""
    with Path(f"{configfile}").open("r") as file:
        __configs = yaml.load(file)

    __exports: list = [
        [
            "index",
            "codec",
            "type",
            "preset",
            "threads",
            "infile_options",
            "outfile_filename",
            "outfile_size_kbyte",
            "outfile_bit_rate_kbs",
            "outfile_options",
            "elapsed_encode_second",
            "elapsed_encode_time",
            "compression_ratio_persent",
            "compression_speed",
            "ssim_min",
            "ssim_harmonic_mean",
            "vmaf_min",
            "vmaf_harmonic_mean",
        ],
    ]

    for __index, __config in enumerate(__configs["encodes"]):
        __exports.extend(
            [
                [
                    __index,
                    __config["codec"],
                    __config["type"],
                    __config["preset"],
                    __config["threads"],
                    __config["infile"]["option"],
                    __config["outfile"]["filename"],
                    __config["outfile"]["size_kbyte"],
                    __config["outfile"]["bit_rate_kbs"],
                    __config["outfile"]["options"],
                    __config["elapsed"]["encode"]["second"],
                    __config["elapsed"]["encode"]["time"],
                    __config["results"]["compression"]["ratio_persent"],
                    __config["results"]["compression"]["speed"],
                    __config["results"]["vmaf"]["pooled_metrics"]["float_ssim"]["min"],
                    __config["results"]["vmaf"]["pooled_metrics"]["float_ssim"]["harmonic_mean"],
                    __config["results"]["vmaf"]["pooled_metrics"]["vmaf"]["min"],
                    __config["results"]["vmaf"]["pooled_metrics"]["vmaf"]["harmonic_mean"],
                ],
            ],
        )

    with Path(configfile.replace(".yml", ".csv", 1)).open("w") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        for __export in __exports:
            csvwriter.writerow(__export)


def main(configfile: str) -> None:  # noqa: PLR0915
    """Main."""
    __configs: dict = load_config(configfile)
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
                __encode_cfg = yaml.load(file)

            with Path(f"{__basefile}").open("rb") as file:
                __hasher = hashlib.sha256()
                __hasher.update(file.read())
                __encode_cfg["configs"]["basehash"] = f"{__hasher.hexdigest()}"

            __encode_cfg["configs"]["ffmpege"] = {
                "program_version": __base_probe_log["program_version"],
                "library_versions": __base_probe_log["library_versions"],
            }

            with Path(f"{args.config}").open("w") as file:
                yaml.dump(
                    {"configs": __encode_cfg["configs"], "encodes": __encode_cfg["encodes"]},
                    file,
                )
        else:
            print("base to skip encode")  # noqa: T201
            with Path(f"{__basefile.replace(__baseext, '_ffprobe.json', 1)}").open("r") as file:
                __base_probe_log = json.load(file)

        with Path(f"{args.config}").open("r") as file:
            __encode_cfg = yaml.load(file)

        __length: int = len(__encode_cfg["encodes"])
        for __index, __encode in enumerate(__encode_cfg["encodes"]):
            print(  # noqa: T201
                "=" * 80
                + f"\n{__index + 1:0>4}/{__length:0>4} ({(__index + 1) / __length:>7.2%})\n",
            )

            __encode_exec_flg: bool = __encode["outfile"]["hash"] == ""
            print(f"outfile hash:  {__encode['outfile']['hash']}")  # noqa: T201
            print(f"outfile cache: {not __encode_exec_flg}")  # noqa: T201
            if __encode_exec_flg:
                __encode_rep = encoding(
                    encode_cfg=__encode,
                    outputext=__baseext,
                    probe_timeout=int(float(__base_probe_log["format"]["duration"])),
                )
                __vmaf_rsp = getvmaf(encode_cfg=__encode, outputext=__baseext)

                """load filehash."""
                with Path(f"{__encode['outfile']['filename']}{__baseext}").open(
                    "rb",
                ) as file_hash_encode:
                    __hasher = hashlib.sha256()
                    __hasher.update(file_hash_encode.read())
                    __encode_hash = f"{__hasher.hexdigest()}"

                """Load ffproble."""
                with Path(f"{__encode['outfile']['filename']}_ffprobe.json").open("r") as file:
                    __probe_log = json.load(file)

                """Load VMAF."""
                with Path(f"{__encode['outfile']['filename']}_vmaf.json").open("r") as file:
                    __vmaf_log = json.load(file)

                """Write parameters."""
                __encode_cfg["encodes"][__index]["infile"].update(
                    {
                        "duration": float(__base_probe_log["format"]["duration"]),
                        "size_kbyte": (
                            int(
                                __base_probe_log["format"]["size"],
                            )
                            / 1024
                        ),
                    },
                )
                __encode_cfg["encodes"][__index]["outfile"].update(
                    {
                        "bit_rate_kbs": float(
                            (int(__probe_log["format"]["bit_rate"]) / 1024),
                        ),
                        "duration": float(
                            __probe_log["format"]["duration"],
                        ),
                        "hash": __encode_hash,
                        "size_kbyte": (
                            int(
                                __probe_log["format"]["size"],
                            )
                            / 1024
                        ),
                        "stream": __encode_rep["stream"],
                    },
                )
                __encode_cfg["encodes"][__index].update(
                    {
                        "commandline": __encode_rep["commandline"],
                        "elapsed": {
                            "encode": {
                                "second": __encode_rep["elapsed_time"],
                                "time": strftime(
                                    "%H:%M:%S",
                                    gmtime(__encode_rep["elapsed_time"]),
                                ),
                            },
                            "vmaf": {
                                "second": __vmaf_rsp["elapsed_time"],
                                "time": strftime("%H:%M:%S", gmtime(__vmaf_rsp["elapsed_time"])),
                            },
                        },
                        "results": {
                            "compression": {
                                "ratio_persent": (
                                    1
                                    - (
                                        float(__probe_log["format"]["size"])
                                        / float(__base_probe_log["format"]["size"])
                                    )
                                ),
                                "speed": (
                                    float(__probe_log["format"]["duration"])
                                    / __encode_rep["elapsed_time"]
                                ),
                            },
                            "vmaf": {
                                "version": __vmaf_log["version"],
                                "commandline": __vmaf_rsp["commandline"],
                                "pooled_metrics": {
                                    "float_ssim": __vmaf_log["pooled_metrics"]["float_ssim"],
                                    "vmaf": __vmaf_log["pooled_metrics"]["vmaf"],
                                },
                            },
                        },
                    },
                )

                "settings.yml 書き込み"
                with Path(f"{args.config}").open("w") as file:
                    yaml.dump(
                        {"configs": __encode_cfg["configs"], "encodes": __encode_cfg["encodes"]},
                        file,
                    )


if __name__ == "__main__":
    main(configfile=args.config)
    getcsv(configfile=args.config)
