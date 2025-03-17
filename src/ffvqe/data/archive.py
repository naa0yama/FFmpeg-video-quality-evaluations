#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Archive functionality for FFmpeg video quality evaluations."""

import json
from pathlib import Path
import shutil
from typing import Any

from ffvqe.config.loader import load_config
from ffvqe.utils.file_operations import compress_files
from ffvqe.utils.yaml_handler import create_yaml_handler


def archive(config_path: str, args: object) -> None:
    """Archive encoding results and data files.

    Compresses log files, moves data files to the assets directory,
    and updates configuration references.

    Args:
        config_path: Path to the configuration file.
        args: Command line arguments.
    """
    __configs: dict[str, Any] = load_config(configfile=config_path, args=args)
    __configfile: Path = Path(config_path)
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
    __archive_files: list[Path] = []
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
        if file.exists():
            shutil.move(f"{file}", f"{__assetdir.parent}/{file.name}")
            print(f"[ARCHIVE] move: {file} to {__assetdir.parent}/{file.name}")  # noqa: T201
        else:
            print(f"[ARCHIVE] file not found: {file}")  # noqa: T201

    yaml = create_yaml_handler()
    with Path(f"{__assetdir.parent}/{__configfile.name}").open("r") as __file:
        ____data = yaml.load(__file)
    ____data["configs"]["datafile"] = f"{__assetdir.parent}/{__datafile.name}"

    print(f"[ARCHIVE] dataset name overwrite file: {__assetdir.parent}/{__datafile.name}")  # noqa: T201
    with Path(f"{__assetdir.parent}/{__configfile.name}").open("w") as ___file:
        yaml.dump(____data, ___file)

    if __basedir.exists():
        print(f"[ARCHIVE] remove dist directory: {__basedir}")  # noqa: T201
        __basedir.rmdir()
