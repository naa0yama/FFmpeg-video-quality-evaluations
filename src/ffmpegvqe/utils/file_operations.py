#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""File operation utilities for FFmpeg video quality evaluations."""

import hashlib
from pathlib import Path
import tarfile


def getfilehash(filename: str) -> str:
    """Calculate SHA-256 hash of a file.

    Args:
        filename: Path to the file to hash.

    Returns:
        The hexadecimal digest of the file's SHA-256 hash.
    """
    with Path(f"{filename}").open("rb") as file:
        __hasher = hashlib.sha256()
        __hasher.update(file.read())

    return f"{__hasher.hexdigest()}"


def compress_files(dst: Path, files: list[Path]) -> None:
    """Create a tar archive of the given files.

    Args:
        dst: Destination directory path.
        files: List of file paths to compress.
    """
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
