#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Encoding functionality for FFmpeg video quality evaluations."""

from functools import partial
import json
from os import environ
from pathlib import Path
import subprocess
import time
from typing import Any

from ffmpeg_progress_yield import FfmpegProgress
from tqdm import tqdm as std_tqdm

from ffmpegvqe.encoding.frame_info import getframeinfo
from ffmpegvqe.utils.time_format import format_seconds

# tqdmのカスタム設定
tqdm = partial(
    std_tqdm,
    bar_format="{desc:92}{percentage:5.0f}%|{bar:20}{r_bar}",
    dynamic_ncols=True,
    ncols=155,
)


def _build_ffmpeg_command(encode_cfg: dict[str, Any], ffmpeg_threads: int) -> list[str]:
    """Build FFmpeg command from encoding configuration.

    Args:
        encode_cfg: Dictionary containing encoding configuration.
        ffmpeg_threads: Number of threads to use for FFmpeg encoding.

    Returns:
        List of command arguments for FFmpeg.
    """
    ffmpeg_cmd: list[str] = [
        "ffmpeg",
        "-y",
        "-threads",
        f"{ffmpeg_threads}",
    ]

    # Add hardware acceleration options if specified
    if encode_cfg["hwaccels"] != "":
        ffmpeg_cmd.extend(str(encode_cfg["hwaccels"]).split())

    # Add input file options
    if "infile" in encode_cfg:
        if encode_cfg["infile"]["option"] != "":
            ffmpeg_cmd.extend(str(encode_cfg["infile"]["option"]).split())
        ffmpeg_cmd.append("-i")
        ffmpeg_cmd.append(f"{encode_cfg['infile']['filename']}")

    # Add output file options
    if "outfile" in encode_cfg:
        if encode_cfg["outfile"]["options"] != []:
            ffmpeg_cmd.extend(str(encode_cfg["outfile"]["options"]).split())
        ffmpeg_cmd.append("-c:v")
        ffmpeg_cmd.append(f"{encode_cfg['codec']}")

        if encode_cfg["preset"] != "none":
            ffmpeg_cmd.append("-preset:v")
            ffmpeg_cmd.append(f"{encode_cfg['preset']}")

        ffmpeg_cmd.append(f"{encode_cfg['outfile']['filename']}.mkv")

    return ffmpeg_cmd


def _run_ffmpeg_encode(encode_cfg: dict[str, Any], ffmpeg_cmd: list[str]) -> float:
    """Run FFmpeg encoding process with progress tracking.

    Args:
        encode_cfg: Dictionary containing encoding configuration.
        ffmpeg_cmd: List of command arguments for FFmpeg.

    Returns:
        Elapsed time for encoding in seconds.
    """
    # Ensure output directory exists
    if not Path(f"{encode_cfg['outfile']['filename']}").parent.exists():
        Path.mkdir(Path(f"{encode_cfg['outfile']['filename']}").parent, parents=True)

    print(f"__ffmpege_cmd: {ffmpeg_cmd}")  # noqa: T201
    environ["FFREPORT"] = f"file={encode_cfg['outfile']['filename']}.log:level=40"

    # Start encoding and track progress
    start_time = time.time()
    ff_encode = FfmpegProgress(ffmpeg_cmd)
    with tqdm(
        desc=f"[ENCODE] {encode_cfg['outfile']['filename']}.log",
        total=100,
        position=1,
    ) as pbar:
        for progress in ff_encode.run_command_with_progress():
            pbar.update(progress - pbar.n)

    # Clean up environment and calculate elapsed time
    environ.pop("FFREPORT", None)
    elapsed_time = time.time() - start_time
    print(f"\nelapsed_time: {format_seconds(int(elapsed_time))}\n")  # noqa: T201

    return elapsed_time


def _run_ffprobe(encode_cfg: dict[str, Any], probe_timeout: int) -> tuple[str, float]:
    """Run FFprobe on encoded file to extract information.

    Args:
        encode_cfg: Dictionary containing encoding configuration.
        probe_timeout: Timeout in seconds for the FFprobe command.

    Returns:
        Tuple of (probe_filename, elapsed_time).

    Raises:
        subprocess.TimeoutExpired: If FFprobe process times out.
    """
    probe_filename: str = f"{encode_cfg['outfile']['filename']}_ffprobe.json"
    probe_cmd: list[str] = [
        "ffprobe",
        "-v",
        "error",
        "-hide_banner",
        "-show_streams",
        "-show_format",
        "-show_entries",
        "frame=pict_type",
        "-print_format",
        "json",
        "-i",
        f"{encode_cfg['outfile']['filename']}.mkv",
        "-o",
        probe_filename,
    ]

    # Start FFprobe process and track progress
    start_time = time.time()
    process = subprocess.Popen(args=probe_cmd)

    for _timeout in tqdm(
        range(probe_timeout),
        desc=f"[PROBE ] {probe_filename}",
        unit="s",
    ):
        time.sleep(1)
        if process.poll() is not None:
            break

    elapsed_time = time.time() - start_time

    # Check if process timed out
    if process.poll() is None:
        process.terminate()
        raise subprocess.TimeoutExpired(probe_cmd, probe_timeout)

    return probe_filename, elapsed_time


def encoding(
    encode_cfg: dict[str, Any],
    probe_timeout: int,
    ffmpeg_threads: int = 4,
) -> dict[str, Any]:
    """Encode video using FFmpeg with the specified configuration.

    Executes FFmpeg with the provided encoding configuration and monitors progress.
    After encoding, runs FFprobe to extract information about the encoded file.

    Args:
        encode_cfg: Dictionary containing encoding configuration.
        probe_timeout: Timeout in seconds for the FFprobe command.
        ffmpeg_threads: Number of threads to use for FFmpeg encoding.

    Returns:
        Dictionary containing encoding results including:
        - commandline: The full FFmpeg command used
        - elapsed_time: Time taken for encoding
        - elapsed_prbt: Time taken for probing
        - stream: Stream information from FFprobe
    """
    # Build FFmpeg command
    ffmpeg_cmd = _build_ffmpeg_command(encode_cfg, ffmpeg_threads)

    # Run FFmpeg encoding
    elapsed_time_enc = _run_ffmpeg_encode(encode_cfg, ffmpeg_cmd)

    # Run FFprobe on encoded file
    probe_filename, elapsed_time_prbt = _run_ffprobe(encode_cfg, probe_timeout)

    # Return results
    return {
        "commandline": " ".join(ffmpeg_cmd),
        "elapsed_time": elapsed_time_enc,
        "elapsed_prbt": elapsed_time_prbt,
        "stream": getframeinfo(probe_filename),
    }


def getvmaf(encode_cfg: dict[str, Any], cpu_count: int | None = None) -> dict[str, Any]:
    """Calculate VMAF score for encoded video.

    Compares the encoded video with the original reference video to calculate
    VMAF, PSNR, and SSIM quality metrics.

    Args:
        encode_cfg: Dictionary containing encoding configuration.
        cpu_count: Number of CPU cores to use for VMAF calculation.

    Returns:
        Dictionary containing VMAF calculation results including:
        - commandline: The full FFmpeg command used
        - elapsed_time: Time taken for VMAF calculation
    """
    if cpu_count is None:
        from os import cpu_count as os_cpu_count

        cpu_count = os_cpu_count()

    __ffmpege_cmd: list[str] = [
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
            f"n_threads={cpu_count}:"
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


def getprobe(videofile: str) -> None:
    """Run FFprobe on a video file to extract information.

    Executes FFprobe to extract detailed information about a video file
    and saves the output as JSON.

    Args:
        videofile: Path to the video file to probe.
    """
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


def get_versions(configfile: str) -> dict[str, Any]:
    """Get FFmpeg version information.

    Retrieves version information for FFmpeg and its libraries.

    Args:
        configfile: Path to the configuration file.

    Returns:
        Dictionary containing FFmpeg version information.
    """
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
        __versions_log: dict[str, Any] = json.load(file)
    __versions_file.unlink()

    __versions_build: dict[str, Any] = {}
    """__versions_build_file がある"""
    if Path(f"{__versions_build_file}").exists():
        print(f"[GET   ] {__versions_build_file} file found.")  # noqa: T201
        with Path(f"{__versions_build_file}").open("r") as file:
            from ffmpegvqe.utils.yaml_handler import create_yaml_handler

            yaml = create_yaml_handler()
            __versions_build = yaml.load(file)

    return {
        "ffmpege": {
            "program_version": __versions_log["program_version"],
            "library_versions": __versions_log["library_versions"],
        },
        "packages": __versions_build,
    }
