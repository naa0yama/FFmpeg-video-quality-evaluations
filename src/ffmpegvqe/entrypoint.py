#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""entrypoint."""

# Standard Library
import argparse
from functools import partial
import hashlib
import json
from os import cpu_count
from os import environ
from os import fsync
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
from time import gmtime
from time import strftime
from typing import Any
from uuid import uuid4

import duckdb
from ffmpeg_progress_yield import FfmpegProgress
import ruamel.yaml
from tqdm import tqdm as std_tqdm


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
    "-a",
    "--archive",
    help="Archives bench data.",
    action="store_true",
)
parser.add_argument(
    "--codec",
    help='Template codec. (defualt="all")',
    type=str,
    default="all",
)
parser.add_argument(
    "--type",
    help='Template Bitrate control modes. (CRF | CQP | ICQ) (defualt="all")',
    type=str,
    default="all",
)
parser.add_argument(
    "--config",
    help="config file path. (e.g): ./videos/settings.yml",
    required=True,
    type=str,
)
parser.add_argument(
    "--overwrite",
    help="Overriding datafile. (default: False)",
    action="store_true",
)
parser.add_argument(
    "--encode",
    help="encode mode. (default: False)",
    action="store_true",
)
parser.add_argument(
    "-fthreads",
    "--ffmpeg-threads",
    help="Set the number of threads to be used (default: 4)",
    type=int,
    default=4,
)
parser.add_argument(
    "--dist-save-video",
    help="Automatically delete transcoded videos in Dist folder. (default: False)",
    action="store_true",
)
args = parser.parse_args()

tqdm = partial(
    std_tqdm,
    bar_format="{desc:92}{percentage:5.0f}%|{bar:20}{r_bar}",
    dynamic_ncols=True,
    ncols=155,
)


def getframeinfo(filename: str) -> dict:
    """Get frame Information."""
    __probe_log: dict = {}
    __stream: dict = {
        "gop": 0,
        "has_b_frames": 0,
        "refs": 0,
        "frames": {"I": 0, "P": 0, "B": 0, "total": 0},
    }
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
    __stream["frames"]["total"] = (
        __stream["frames"]["I"] + __stream["frames"]["P"] + __stream["frames"]["B"]
    )

    """ "frames" を削除"""
    if "frames" in __probe_log:
        del __probe_log["frames"]

    with Path(f"{filename}").open("w") as file:
        json.dump(__probe_log, file, indent=2)

    return __stream


def encoding(encode_cfg: dict, probe_timeout: int) -> dict:  # noqa: C901
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

        __ffmpege_cmd.append(f"{encode_cfg['outfile']['filename']}.mkv")

    if not Path(f"{encode_cfg['outfile']['filename']}").parent.exists():
        Path.mkdir(Path(f"{encode_cfg['outfile']['filename']}").parent, parents=True)

    print(f"__ffmpege_cmd: {__ffmpege_cmd}")  # noqa: T201
    environ["FFREPORT"] = f"file={encode_cfg['outfile']['filename']}.log:level=40"
    __enct = time.time()
    __ff_encode = FfmpegProgress(__ffmpege_cmd)
    with tqdm(
        desc=f"[ENCODE] {encode_cfg['outfile']['filename']}.log",
        total=100,
        position=1,
    ) as pbar:
        for progress in __ff_encode.run_command_with_progress():
            pbar.update(progress - pbar.n)
    environ.pop("FFREPORT", None)
    __elapsed_time_enc = time.time() - __enct
    print(f"\nelapsed_time: {format_seconds(int(__elapsed_time_enc))}\n")  # noqa: T201

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
        f"{encode_cfg['outfile']['filename']}.mkv",
        "-o",
        __probe_filename,
    ]
    __prbt = time.time()
    process = subprocess.Popen(
        args=__proble_cmd,
    )
    for _timeout in tqdm(
        range(probe_timeout),
        desc=f"[PROBE ] {__probe_filename}",
        unit="s",
    ):
        time.sleep(1)
        if process.poll() is not None:
            break
    __elapsed_time_prbt = time.time() - __prbt
    if process.poll() is None:
        process.terminate()
        raise subprocess.TimeoutExpired(__proble_cmd, probe_timeout)

    return {
        "commandline": " ".join(__ffmpege_cmd),
        "elapsed_time": __elapsed_time_enc,
        "elapsed_prbt": __elapsed_time_prbt,
        "stream": getframeinfo(f"{__probe_filename}"),
    }


def getvmaf(encode_cfg: dict) -> dict:
    """Get VMAF."""
    __ffmpege_cmd: list = [
        "ffmpeg",
        "-r",
        "29.97",
        "-i",
        f"{encode_cfg['outfile']['filename']}.mkv",
        "-r",
        "29.97",
        "-i",
        f"{encode_cfg['infile']['filename']}",
        "-lavfi",
        (
            "[0:v]settb=AVTB,setpts=PTS-STARTPTS[Distorted];"
            "[1:v]settb=AVTB,setpts=PTS-STARTPTS[Reference];"
            "[Distorted][Reference]libvmaf=eof_action=endall:"
            "log_fmt=json:"
            f"log_fmt=json:log_path={encode_cfg['outfile']['filename']}_vmaf.json:"
            f"n_threads={cpu_count()}:"
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
        desc=f"[VMAF  ] {encode_cfg['outfile']['filename']}_vmaf.json",
        total=100,
        position=1,
    ) as pbar:
        for progress in __ff_vmaf.run_command_with_progress():
            pbar.update(progress - pbar.n)
    elapsed_time = time.time() - __start

    print(f"\nelapsed_time: {format_seconds(int(elapsed_time))}\n")  # noqa: T201
    return {
        "commandline": " ".join(__ffmpege_cmd),
        "elapsed_time": elapsed_time,
    }


def getfilehash(filename: str) -> str:
    """Get filehash."""
    with Path(f"{filename}").open("rb") as file:
        __hasher = hashlib.sha256()
        __hasher.update(file.read())

    return f"{__hasher.hexdigest()}"


def get_versions(configfile: str) -> dict:
    """Get ffmpge versions."""
    __versions_file: Path = Path(f"{Path(configfile).parent}/versions.json")
    __versions_build_file: Path = Path("/opt/ffmpeg/versions.json")
    print(f"[PROBE ] {__versions_file}")  # noqa: T201
    subprocess.run(
        args=[
            "ffprobe",
            "-v",
            "error",
            "-hide_banner",
            "-show_library_versions",
            "-show_program_version",
            "-print_format",
            "json",
            "-o",
            f"{__versions_file}",
        ],
        timeout=10,
        check=True,
    )

    with __versions_file.open("r") as file:
        __versions_log: dict = json.load(file)
    __versions_file.unlink()

    """__versions_build_file がある"""
    if Path(f"{__versions_build_file}").exists():
        print(f"[GET   ] {__versions_build_file} file found.")  # noqa: T201
        with Path(f"{__versions_build_file}").open("r") as file:
            __versions_build: dict = yaml.load(file)

    return {
        "ffmpege": {
            "program_version": __versions_log["program_version"],
            "library_versions": __versions_log["library_versions"],
        },
        "packages": __versions_build,
    }


def getprobe(videofile: str) -> None:
    """Get probe."""
    __probe_file: Path = Path(
        f"{videofile}".replace(Path(videofile).suffix, "_ffprobe.json", 1),
    )
    print(f"[PROBE ] {__probe_file}")  # noqa: T201
    subprocess.run(
        args=[
            "ffprobe",
            "-v",
            "error",
            "-hide_banner",
            "-show_chapters",
            "-show_format",
            "-show_programs",
            "-show_streams",
            "-print_format",
            "json",
            "-o",
            f"{__probe_file}",
            f"{videofile}",
        ],
        timeout=10,
        check=True,
    )


def load_config(configfile: str) -> dict:  # noqa: PLR0915, PLR0912, C901
    """Load config."""
    __configs: dict = {}
    __config_flag: bool = False
    __encode_cfg: list = []
    __distdir: Path = Path(f"./videos/dist/{Path(configfile).name.replace('.yml', '')}")
    __patterns: list = [
        {
            "codec": "libx264",
            "type": "CRF",
            "comments": "",
            "presets": ["medium"],
            "infile": {"option": ""},
            "outfile": {
                "options": [
                    "-crf 23",
                ],
            },
            "hwaccels": "",
        },
        {
            "codec": "libx265",
            "type": "CRF",
            "comments": "",
            "presets": ["medium"],
            "infile": {"option": ""},
            "outfile": {
                "options": [
                    "-crf 28",
                ],
            },
            "hwaccels": "",
        },
        {
            "codec": "libsvtav1",
            "type": "CRF",
            "comments": "",
            "presets": ["6"],
            "infile": {"option": ""},
            "outfile": {
                "options": [
                    "-crf 35",
                ],
            },
            "hwaccels": "",
        },
        {
            "codec": "h264_qsv",
            "type": "CQP",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-q:v 25",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "h264_qsv",
            "type": "ICQ",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-global_quality 25",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "h264_qsv",
            "type": "LA_ICQ",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-global_quality 25 -look_ahead 1",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "hevc_qsv",
            "type": "CQP",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-q:v 22",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "hevc_qsv",
            "type": "ICQ",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-global_quality 22",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "av1_qsv",
            "type": "CQP",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-q:v 35",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
        {
            "codec": "av1_qsv",
            "type": "ICQ",
            "comments": "",
            "presets": ["veryslow"],
            "infile": {"option": "-hwaccel qsv -c:v mpeg2_qsv"},
            "outfile": {
                "options": [
                    "-global_quality 35",
                ],
            },
            "hwaccels": "-hwaccel_output_format qsv",
        },
    ]
    if args.codec != "all":
        if args.type == "all":
            __patterns = [d for d in __patterns if args.codec == d.get("codec")]
        else:
            __patterns = [
                d
                for d in __patterns
                if args.codec == d.get("codec") and args.type == d.get("type")
            ]

    "configfile ディレクトリが存在しない場合は作成"
    if not Path(configfile).parent.exists():
        Path.mkdir(Path(configfile).parent, parents=True)

    "settings.yml がある"
    if Path(f"{configfile}").exists():
        print(f"{configfile} file found.")  # noqa: T201
        with Path(f"{configfile}").open("r") as file:
            __configs = yaml.load(file)
    else:
        __config_flag = True
        __configs = {
            "configs": {
                "references": [
                    {
                        "name": "ABBB",
                        "type": "Anime",
                        "basefile": "./videos/source/ABBB_MPEG-2_1920x1080_30p.m2ts",
                        "basehash": "f005791ab9cabdc4468317d5d58becf3eb6228a49c6fad09e0923685712af769",
                    },
                    {
                        "name": "ASintel",
                        "type": "Anime",
                        "basefile": "./videos/source/ASintel_MPEG-2_1920x1080_30p.m2ts",
                        "basehash": "8554804c935a382384eed9196ff88bd561767b6be1786aa4921087f265d92f3a",
                    },
                    {
                        "name": "AToS",
                        "type": "Anime",
                        "basefile": "./videos/source/AToS_MPEG-2_1920x1080_30p.m2ts",
                        "basehash": "ff6a0c366a3c631cf76d20c205cf505f964c9126551bf5bf10e8d99f9d04df52",
                    },
                    {
                        "name": "NAir",
                        "type": "Nature",
                        "basefile": "./videos/source/NAir_MPEG-2_1920x1080_30p.m2ts",
                        "basehash": "aec5612c556567df8cc3b37010c2850f709054293f1d5d0b96c68b349c2a97a2",
                    },
                    {
                        "name": "NArmy",
                        "type": "Nature",
                        "basefile": "./videos/source/NArmy_MPEG-2_1920x1080_30p.m2ts",
                        "basehash": "aef3503a79fcacf0e65e368416b0b0b85e54b8eb77e2613a4b750b59fb2b50d5",
                    },
                    {
                        "name": "NNavy",
                        "type": "Nature",
                        "basefile": "./videos/source/NNavy_MPEG-2_1920x1080_30p.m2ts",
                        "basehash": "52409e9400315916bb191dfafe4edd415204671ae00e2ddb447671f4850876cb",
                    },
                ],
                "datafile": "",
                "patterns": __patterns,
            },
        }

    __datafile: str = __configs["configs"]["datafile"]
    __results_list: list = []

    """reference filehash を埋める."""
    for _index, _ref in enumerate(__configs["configs"]["references"]):
        if not Path(
            f"{_ref['basefile'].replace(Path(_ref['basefile']).suffix, '_ffprobe.json', 1)}",
        ).exists():
            if __configs["configs"]["references"][_index]["basehash"] != getfilehash(
                _ref["basefile"],
            ):
                __msg: str = f"Error: references name: {_ref['name']}, basehash not match."
                raise VQEError(__msg)
            print(f"References name: {_ref['name']}, basehash successfull.")  # noqa: T201
            getprobe(videofile=_ref["basefile"])

    """__datafile が設定されてなく、"""
    if __configs["configs"]["datafile"] == "":
        __datafile = f"{Path(configfile).parent}/data{str(uuid4())[24:]}.json"
        __configs["configs"]["datafile"] = __datafile

    elif Path(__datafile).exists() and not args.overwrite:
        """__datafile がある and --overwrite フラグがない."""
        with Path(__datafile).open("r") as file:
            __encode_cfg = json.load(file)

    __existing_encodes = {encode["id"]: encode for encode in __encode_cfg}
    __results_list.extend(__encode_cfg)

    for __pattern in __configs["configs"]["patterns"]:
        __presets: list = __pattern["presets"]
        for __preset in __presets:
            if type(__pattern["outfile"]["options"]) is not list:
                __msg = f"outfile.options is must list[str] : {__pattern['outfile']['options']}"
                raise VQEError(__msg)
            for __out_option in __pattern["outfile"]["options"]:
                for __ref in __configs["configs"]["references"]:
                    __codec: str = __pattern["codec"]
                    __type: str = __pattern["type"]
                    __comments: str = __pattern["comments"]
                    __threads: str = args.ffmpeg_threads
                    __infile_opts: str = __pattern["infile"]["option"]
                    __hwaccels: str = __pattern["hwaccels"]
                    __out_option_hash: str = hashlib.sha256(
                        str(
                            [
                                f"{__codec}{__type}{__preset}{__out_option}",
                                f"{__threads}{__hwaccels}{__infile_opts}",
                            ],
                        ).encode(),
                    ).hexdigest()
                    __out_id_hash: str = hashlib.sha256(
                        str(f"{__ref['basefile']}{__ref['basehash']}{__out_option_hash}").encode(),
                    ).hexdigest()

                    __result_template: dict = {
                        "id": f"{__out_id_hash}",
                        "id_opt": f"{__out_option_hash}",
                        "codec": __codec,
                        "type": __type,
                        "comments": __comments,
                        "preset": __preset,
                        "threads": __threads,
                        "infile": {
                            "name": __ref["name"],
                            "type": __ref["type"],
                            "filename": __ref["basefile"],
                            "duration": 0.0,
                            "size_kbyte": 0.0,
                            "option": __infile_opts,
                        },
                        "outfile": {
                            "filename": f"{__distdir}/{__out_id_hash[:12]}",
                            "options": __out_option,
                            "hash": "",
                            "bit_rate_kbs": 0.0,
                            "duration": 0.0,
                            "size_kbyte": 0.0,
                            "stream": {
                                "gop": 0,
                                "has_b_frames": 0,
                                "refs": 0,
                                "frames": {"I": 0, "P": 0, "B": 0, "total": 0},
                            },
                        },
                        "commandline": "",
                        "hwaccels": __hwaccels,
                        "results": {
                            "encode": {
                                "second": 0.0,
                                "time": "",
                                "fps": 0,
                                "speed": 0.0,
                            },
                            "compression_ratio_persent": 0.0,
                            "probe": {
                                "second": 0.0,
                                "time": "",
                            },
                            "vmaf": {
                                "second": 0.0,
                                "time": "",
                                "version": "",
                                "commandline": "",
                                "pooled_metrics": {
                                    "float_ssim": {
                                        "min": 0.0,
                                        "max": 0.0,
                                        "mean": 0.0,
                                        "harmonic_mean": 0.0,
                                    },
                                    "vmaf": {
                                        "min": 0.0,
                                        "max": 0.0,
                                        "mean": 0.0,
                                        "harmonic_mean": 0.0,
                                    },
                                },
                            },
                        },
                    }

                    # 既存の encodes と比較して削除または追加
                    if __result_template["id"] not in __existing_encodes:
                        __results_list.append(__result_template)
                        print(  # noqa: T201
                            "encode new ...",
                            f"basefile: {__ref['name']:12}",
                            f"preset: {__result_template['preset']:8}",
                            f"codec: {__result_template['codec']:12}",
                            f"type: {__result_template['type']:24}",
                            f"options: {__result_template['outfile']['options']}",
                        )

    """add ffmpeg versions."""
    __configs["configs"]["environment"] = get_versions(configfile=configfile)
    print(f"\n\n{len(__results_list)} pattern generate.\n\n")  # noqa: T201
    with Path(configfile).open("w") as file:
        yaml.dump(__configs, file)

    if len(__existing_encodes) == len(__results_list):
        print(f"Exitst {__datafile} no updated.")  # noqa: T201
    elif __config_flag is True:
        print(f"Create datafile is {__datafile} write.")  # noqa: T201
        with Path(__datafile).open("w") as file:
            json.dump([], file)
    elif __config_flag is False:
        print(f"{len(__results_list)} pattern is {__datafile} write.")  # noqa: T201
        with Path(__datafile).open("w") as file:
            __encode_cfg = __results_list
            json.dump(__encode_cfg, file)

    return {
        "configs": __configs["configs"],
        "datafile": __datafile,
    }


def getcsv(datafile: dict) -> None:
    """Get csv."""
    with Path(f"{datafile}").open("r") as file:
        __datafile: list = yaml.load(file)
    print(f"[CSV   ] load {datafile} ....")  # noqa: T201

    if __datafile != []:
        __csvfile_all: str = f"{datafile}".replace(".json", "_all.csv", 1)
        __csvfile_type: str = f"{datafile}".replace(".json", "_gby_type.csv", 1)
        __csvfile_option: str = f"{datafile}".replace(".json", "_gby_option.csv", 1)

        duckdb.execute(
            f"""
                CREATE TEMPORARY TABLE encodes AS
                SELECT *
                FROM read_json('{datafile}')
            """,  # noqa: S608
        )

        print(f"[CSV   ] Export csv ..... {__csvfile_all}")  # noqa: T201
        duckdb.sql(
            r"""
            SELECT
                row_number() OVER () - 1                               AS index,
                codec                                                  AS codec,
                type                                                   AS type,
                preset                                                 AS preset,
                threads                                                AS threads,
                infile.name                                            AS ref_name,
                infile.type                                            AS ref_type,
                infile.option                                          AS infile_option,
                outfile.filename                                       AS outfile_filename,
                outfile.size_kbyte                                     AS outfile_size_kbyte,
                outfile.bit_rate_kbs                                   AS outfile_bit_rate_kbs,
                outfile.options                                        AS outfile_options,
                results.encode.second                                  AS enc_sec,
                results.encode.time                                    AS enc_time,
                results.compression_ratio_persent                      AS comp_ratio_persent,
                results.encode.speed                                   AS enc_speed,
                results.vmaf.pooled_metrics.float_ssim.min             AS ssim_min,
                results.vmaf.pooled_metrics.float_ssim.harmonic_mean   AS ssim_mean,
                results.vmaf.pooled_metrics.vmaf.min                   AS vmaf_min,
                results.vmaf.pooled_metrics.vmaf.harmonic_mean         AS vmaf_mean,
            FROM encodes
            """,
        ).write_csv(__csvfile_all)

        print(f"[CSV   ] Export csv ..... {__csvfile_type}")  # noqa: T201
        duckdb.sql(
            r"""
            SELECT
                row_number() OVER () - 1                                   AS index,
                codec                                                      AS codec,
                type                                                       AS type,
                preset                                                     AS preset,
                threads                                                    AS threads,
                infile.type                                                AS ref_type,
                AVG(outfile.size_kbyte)                                    AS outfile_size_kbyte,
                AVG(outfile.bit_rate_kbs)                                  AS outfile_bit_rate_kbs,
                outfile.options                                            AS outfile_options,
                AVG(results.encode.second)                                 AS enc_sec,
                AVG(results.compression_ratio_persent)                     AS comp_ratio_persent,
                AVG(results.encode.speed)                                  AS enc_speed,
                AVG(results.vmaf.pooled_metrics.float_ssim.min)            AS ssim_min,
                AVG(results.vmaf.pooled_metrics.float_ssim.harmonic_mean)  AS ssim_mean,
                AVG(results.vmaf.pooled_metrics.vmaf.min)                  AS vmaf_min,
                AVG(results.vmaf.pooled_metrics.vmaf.harmonic_mean)        AS vmaf_mean,
            FROM encodes
            GROUP BY codec, type, preset, threads, ref_type, outfile_options

            """,
        ).write_csv(__csvfile_type)

        print(f"[CSV   ] Export csv ..... {__csvfile_option}")  # noqa: T201
        duckdb.sql(
            r"""
            SELECT
                row_number() OVER () - 1                                   AS index,
                codec                                                      AS codec,
                type                                                       AS type,
                preset                                                     AS preset,
                threads                                                    AS threads,
                AVG(outfile.size_kbyte)                                    AS outfile_size_kbyte,
                AVG(outfile.bit_rate_kbs)                                  AS outfile_bit_rate_kbs,
                outfile.options                                            AS outfile_options,
                AVG(results.encode.second)                                 AS enc_sec,
                AVG(results.compression_ratio_persent)                     AS comp_ratio_persent,
                AVG(results.encode.speed)                                  AS enc_speed,
                AVG(results.vmaf.pooled_metrics.float_ssim.min)            AS ssim_min,
                AVG(results.vmaf.pooled_metrics.float_ssim.harmonic_mean)  AS ssim_mean,
                AVG(results.vmaf.pooled_metrics.vmaf.min)                  AS vmaf_min,
                AVG(results.vmaf.pooled_metrics.vmaf.harmonic_mean)        AS vmaf_mean,
            FROM encodes
            GROUP BY codec, type, preset, threads, outfile_options

            """,
        ).write_csv(__csvfile_option)
        print("[CSV   ] Export csv done.")  # noqa: T201


def compress_files(dst: Path, files: list) -> None:
    """Create Tar Archive."""
    if not files:
        print("[ARCHIVE] Compress file not found.")  # noqa: T201
        return
    archive_name = f"{dst.parent}/logs_archive.tar.xz"

    print(f"\n\n[ARCHIVE] Create archive file: {archive_name}")  # noqa: T201
    with tarfile.open(archive_name, "w:xz") as tar:
        __length: int = len(files)
        for __index, file_path in enumerate(files):
            tar.add(file_path, arcname=file_path.name)
            print(  # noqa: T201
                f"[ARCHIVE] {__index + 1:0>4}/{__length:0>4} ({(__index + 1) / __length:>7.2%})"
                f" Add compress file: {file_path.name}",
            )
    print("[ARCHIVE] Create archive file done.")  # noqa: T201

    for file in files:
        Path(file).unlink()
        print(f"[ARCHIVE] remove : {file}")  # noqa: T201

    if dst.exists():
        dst.rmdir()
        print(f"[ARCHIVE] rmdir  : {dst}")  # noqa: T201


def archive() -> None:
    """Archives."""
    __configs: dict = load_config(configfile=args.config)
    __configfile: Path = Path(args.config)
    __basedir: Path = Path(f"./videos/dist/{__configfile.name.replace('.yml', '')}")
    __datafile: Path = Path(f"{__configs['configs']['datafile']}")
    __datafilecsv_all: Path = Path(f"{__datafile}".replace(".json", "_all.csv"))
    __datafilecsv_gby_option: Path = Path(f"{__datafile}".replace(".json", "_gby_option.csv"))
    __datafilecsv_gby_type: Path = Path(f"{__datafile}".replace(".json", "_gby_type.csv"))
    __assetdir: Path = Path(f"./assets/{__basedir.name}/logs")
    __assetdir.mkdir(parents=True, exist_ok=True)

    with Path(f"{__datafile}").open("r") as __file:
        __data = json.load(__file)

    __hashs: int = len(
        [encode["outfile"]["hash"] for encode in __data if encode["outfile"]["hash"] != ""],
    )

    if (__hashs) != len(__data):
        print(  # noqa: T201
            f"[ARCHIVE] \n\ndatafile {__datafile} is hashs {__hashs} to encodes {len(__data)}.\n"
            "archive process stop.",
        )
        return

    """move to __assetdir"""
    __archive_files: list = []
    for _ext in [".json", ".log"]:
        for file_path in __basedir.glob(f"*{_ext}"):
            if file_path.is_file():
                shutil.move(f"{file_path}", f"{__assetdir}/{file_path.name}")
                __archive_files.append(Path(f"{__assetdir}/{file_path.name}"))
                print(f"[ARCHIVE] move: {file_path} to {__assetdir}/{file_path.name}")  # noqa: T201

    """archive vmaf files"""
    compress_files(dst=__assetdir, files=__archive_files)

    """move to configfile, csv datafile"""
    for file in [
        __configfile,
        __datafile,
        __datafilecsv_all,
        __datafilecsv_gby_option,
        __datafilecsv_gby_type,
    ]:
        shutil.move(f"{file}", f"{__assetdir.parent}/{file.name}")
        print(f"[ARCHIVE] move: {file} to {__assetdir.parent}/{file.name}")  # noqa: T201

    with Path(f"{__assetdir.parent}/{__configfile.name}").open("r") as __file:
        ____data = yaml.load(__file)
    ____data["configs"]["datafile"] = f"{__assetdir.parent}/{__datafile.name}"

    print(f"[ARCHIVE] dataset name overwrite file: {__assetdir.parent}/{__datafile.name}")  # noqa: T201
    with Path(f"{__assetdir.parent}/{__configfile.name}").open("w") as ___file:
        yaml.dump(____data, ___file)

    if __basedir.exists():
        print(f"[ARCHIVE] remove dist directory: {__basedir}")  # noqa: T201
        __basedir.rmdir()


def format_seconds(seconds: int) -> str:
    """Format seconds to d%d%Hh%Mm%Ss."""
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{days:02d}d, {hours:02d}h{minutes:02d}m{secs:02d}s"


def main(config: dict) -> None:
    """Main."""
    if args.encode is True:
        __datafile: str = config["configs"]["datafile"]
        with Path(__datafile).open("r") as file:
            __encode_cfg = json.load(file)

        __length: int = len(__encode_cfg)
        __rapt: int = 0
        for __index, __encode in enumerate(__encode_cfg):
            print(  # noqa: T201
                "=" * 155
                + f"\n{__index + 1:0>4}/{__length:0>4} ({(__index + 1) / __length:>7.2%})\t"
                + f"Lap time: {format_seconds(int(__rapt))} ({int(__rapt)}s)\t"
                + f"ETA: {format_seconds(int(__rapt * (__length - __index)))}\n",
            )
            __basefile: str = __encode["infile"]["filename"]
            with Path(f"{__basefile.replace(Path(__basefile).suffix, '_ffprobe.json', 1)}").open(
                "r",
            ) as file:
                __base_probe_log = json.load(file)

            __encode_exec_flg: bool = __encode["outfile"]["hash"] == ""
            print(f"outfile hash:  {__encode['outfile']['hash']}")  # noqa: T201
            print(f"outfile cache: {not __encode_exec_flg}")  # noqa: T201

            """Batch encode start."""
            if __encode_exec_flg:
                try:
                    __encode_rep = encoding(
                        encode_cfg=__encode,
                        probe_timeout=int(float(__base_probe_log["format"]["duration"]) * 1.2),
                    )
                    __vmaf_rsp = getvmaf(encode_cfg=__encode)
                    __rapt = (
                        __encode_rep["elapsed_time"]
                        + __encode_rep["elapsed_prbt"]
                        + __vmaf_rsp["elapsed_time"]
                    )
                except (KeyboardInterrupt, Exception) as err:
                    """__datafile write."""
                    print(f"\n\n{err}: datafile writeing to {__datafile}")  # noqa: T201
                    with Path(__datafile).open("w") as file:
                        json.dump(__encode_cfg, file)
                        file.flush()
                        fsync(file.fileno())
                    print("done.\n\n")  # noqa: T201
                    raise

                """load filehash."""
                __encode_hash = getfilehash(f"{__encode['outfile']['filename']}.mkv")

                if args.dist_save_video is False:
                    Path(f"{__encode['outfile']['filename']}.mkv").unlink()
                    print(f"Automatically delete: {__encode['outfile']['filename']}.mkv")  # noqa: T201

                """Load ffproble."""
                with Path(f"{__encode['outfile']['filename']}_ffprobe.json").open("r") as file:
                    __probe_log = json.load(file)

                """Load VMAF."""
                with Path(f"{__encode['outfile']['filename']}_vmaf.json").open("r") as file:
                    __vmaf_log = json.load(file)

                """Write parameters."""
                __encode["infile"].update(
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
                __encode["outfile"].update(
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
                __encode.update(
                    {
                        "commandline": __encode_rep["commandline"],
                        "results": {
                            "encode": {
                                "second": __encode_rep["elapsed_time"],
                                "time": strftime(
                                    "%H:%M:%S",
                                    gmtime(__encode_rep["elapsed_time"]),
                                ),
                                "fps": (
                                    int(__encode_rep["stream"]["frames"]["total"])
                                    / __encode_rep["elapsed_time"]
                                ),
                                "speed": (
                                    float(__probe_log["format"]["duration"])
                                    / __encode_rep["elapsed_time"]
                                ),
                            },
                            "compression_ratio_persent": (
                                1
                                - (
                                    float(__probe_log["format"]["size"])
                                    / float(__base_probe_log["format"]["size"])
                                )
                            ),
                            "probe": {
                                "second": __encode_rep["elapsed_prbt"],
                                "time": strftime(
                                    "%H:%M:%S",
                                    gmtime(__encode_rep["elapsed_time"]),
                                ),
                            },
                            "vmaf": {
                                "second": __vmaf_rsp["elapsed_time"],
                                "time": strftime(
                                    "%H:%M:%S",
                                    gmtime(__vmaf_rsp["elapsed_time"]),
                                ),
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

                "__datafile 書き込み"
                with Path(__datafile).open("w") as file:
                    json.dump(__encode_cfg, file)
            else:
                __rapt = (
                    __encode["results"]["encode"]["second"]
                    + __encode["results"]["probe"]["second"]
                    + __encode["results"]["vmaf"]["second"]
                )


if __name__ == "__main__":
    if args.archive is True and args.encode is True:
        sys.exit("\n\nCannot be specified together with '--encode' and '--archive'.")

    if args.archive:
        archive()

    else:
        __configs: dict = load_config(configfile=args.config)
        main(config=__configs)
        getcsv(datafile=__configs["configs"]["datafile"])
