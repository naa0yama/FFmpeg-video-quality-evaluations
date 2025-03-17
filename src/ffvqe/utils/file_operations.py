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


def split_large_file(file_path: Path, max_size_mb: int = 80) -> list[Path]:
    """Split a large file into smaller chunks.

    Args:
        file_path: Path to the file to split.
        max_size_mb: Maximum size of each chunk in MB.

    Returns:
        List of paths to the split files.
    """
    if not file_path.exists():
        print(f"[SPLIT] Error: File {file_path} does not exist.")  # noqa: T201
        return []

    file_size = file_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024

    # ファイルサイズが制限以下なら分割不要
    if file_size <= max_size_bytes:
        print(f"[SPLIT] File {file_path} is already under size limit.")  # noqa: T201
        return [file_path]

    # 分割数を計算
    num_parts = (file_size + max_size_bytes - 1) // max_size_bytes
    print(f"[SPLIT] Splitting {file_path} into {num_parts} parts.")  # noqa: T201

    # 分割ファイルのパスリスト
    split_files: list[Path] = []

    # ファイルを読み込んで分割
    with file_path.open("rb") as f_in:
        for i in range(num_parts):
            # 分割ファイル名を生成(例: logs_archive_001.tar.xz)
            # ファイル名を適切に分割(例: "large_file.tar.xz" -> "large_file" + "_001" + ".tar.xz")
            original_name = file_path.name
            # 最初のドットの位置を見つける
            dot_pos = original_name.find(".")
            if dot_pos > 0:
                name_part = original_name[:dot_pos]
                ext_part = original_name[dot_pos:]
                part_filename = f"{name_part}_{i + 1:03d}{ext_part}"
            else:
                # ドットがない場合は単純に連番を付ける
                part_filename = f"{file_path.stem}_{i + 1:03d}{file_path.suffix}"
            part_path = file_path.parent / part_filename

            # 分割ファイルに書き込み
            with part_path.open("wb") as f_out:
                chunk = f_in.read(max_size_bytes)
                if not chunk:
                    break
                f_out.write(chunk)

            print(f"[SPLIT] Created part {i + 1}/{num_parts}: {part_path}")  # noqa: T201
            split_files.append(part_path)

    return split_files


def compress_files(dst: Path, files: list[Path], max_size_mb: int = 80) -> None:
    """Create a tar archive of the given files, split if exceeds size limit.

    Args:
        dst: Destination directory path.
        files: List of file paths to compress.
        max_size_mb: Maximum size of each archive file in MB (default: 80).
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

    # 圧縮後のファイルサイズをチェック
    archive_path = Path(archive_name)
    archive_size = archive_path.stat().st_size

    # サイズ制限を超える場合は分割
    if archive_size > max_size_mb * 1024 * 1024:
        print(  # noqa: T201
            f"[ARCHIVE] Archive size ({archive_size / (1024 * 1024):.2f} MB) exceeds limit ({max_size_mb} MB).",
        )
        print("[ARCHIVE] Splitting archive into multiple files.")  # noqa: T201

        # ファイルを分割
        split_files = split_large_file(archive_path, max_size_mb)

        if split_files:
            # 元のアーカイブを削除
            archive_path.unlink()
            print(f"[ARCHIVE] Removed original large archive: {archive_name}")  # noqa: T201
            print(f"[ARCHIVE] Created {len(split_files)} split archives.")  # noqa: T201

    # 元のファイルを削除
    for file in files:
        Path(file).unlink()
        print(f"[ARCHIVE] remove : {file}")  # noqa: T201

    if dst.exists():
        dst.rmdir()
        print(f"[ARCHIVE] rmdir  : {dst}")  # noqa: T201
