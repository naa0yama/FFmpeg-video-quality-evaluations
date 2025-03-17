#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Main entry point for FFmpeg video quality evaluations."""

import argparse
from functools import partial
import json
from os import fsync
from pathlib import Path
import sys
from time import gmtime
from time import strftime
from typing import Any

from tqdm import tqdm as std_tqdm

from ffvqe._version import __version__
from ffvqe.config.loader import load_config
from ffvqe.data.archive import archive
from ffvqe.data.csv_generator import getcsv
from ffvqe.encoding.encoder import encoding
from ffvqe.encoding.encoder import getvmaf
from ffvqe.summary import main as summary_main
from ffvqe.utils.file_operations import getfilehash
from ffvqe.utils.time_format import format_seconds

# tqdmのカスタム設定
tqdm = partial(
    std_tqdm,
    bar_format="{desc:92}{percentage:5.0f}%|{bar:20}{r_bar}",
    dynamic_ncols=True,
    ncols=155,
)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="FFmpeg video quality encoding quality evaluation.",
    )

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
        "-s",
        "--summary",
        help="Shows a summary table.",
        action="store_true",
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
    parser.add_argument(
        "--auto-download-references",
        help="Automatically download reference files without prompting. (default: False)",
        action="store_true",
    )

    return parser


def main_encode(config: dict[str, Any], args: argparse.Namespace) -> None:
    """Main encoding function.

    Processes encoding configurations and executes encoding and VMAF evaluation.

    Args:
        config: Configuration dictionary.
        args: Command line arguments.
    """
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
                    ffmpeg_threads=args.ffmpeg_threads,
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


def main() -> None:
    """Main entry point for the application.

    Parses command line arguments and executes the appropriate function.
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    print(f"version: {__version__}")  # noqa: T201
    if args.archive is True and args.encode is True:
        sys.exit("\n\nCannot be specified together with '--encode' and '--archive'.")

    if args.archive:
        archive(config_path=args.config, args=args)
        sys.exit("\n\n Archive done.")

    if args.summary:
        summary_main(config_path=args.config, args=args)
        sys.exit("\n\n Summary done.")

    __configs: dict[str, Any] = load_config(configfile=args.config, args=args)
    if args.encode:
        main_encode(config=__configs, args=args)
        getcsv(datafile=__configs["configs"]["datafile"])


if __name__ == "__main__":
    main()
