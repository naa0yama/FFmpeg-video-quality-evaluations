#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Tests for utility functions."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import PropertyMock
from unittest.mock import mock_open
from unittest.mock import patch

from ffvqe.utils.file_operations import compress_files
from ffvqe.utils.file_operations import getfilehash
from ffvqe.utils.file_operations import split_large_file
from ffvqe.utils.time_format import format_seconds


def test_getfilehash() -> None:
    """Test getfilehash function."""
    with patch("pathlib.Path.open", mock_open(read_data=b"dummy content")):
        result = getfilehash("dummy_path")
        expected_hash = hashlib.sha256(b"dummy content").hexdigest()
        assert result == expected_hash


def test_split_large_file_not_exists() -> None:
    """Test split_large_file function when file does not exist."""
    with patch("pathlib.Path.exists", return_value=False):
        result = split_large_file(Path("nonexistent_file"))
        assert result == []


def test_split_large_file_under_limit() -> None:
    """Test split_large_file function when file size is under limit."""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.stat") as mock_stat,
    ):
        # ファイルサイズを70MBに設定, 制限80MB以下
        mock_stat.return_value.st_size = 70 * 1024 * 1024
        result = split_large_file(Path("small_file.tar.xz"))
        assert len(result) == 1
        assert result[0] == Path("small_file.tar.xz")


def test_split_large_file_over_limit() -> None:
    """Test split_large_file function when file size exceeds limit."""
    test_file_path = Path("large_file.tar.xz")
    max_size_mb = 80
    max_size_bytes = max_size_mb * 1024 * 1024

    # 160MBのダミーデータを作成, 2分割されるはず
    dummy_data = b"x" * (max_size_bytes * 2)

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.stat") as mock_stat,
        patch("pathlib.Path.open", mock_open(read_data=dummy_data)),
        patch("pathlib.Path.parent", new_callable=PropertyMock, return_value=Path()),
    ):
        mock_stat.return_value.st_size = len(dummy_data)
        result = split_large_file(test_file_path, max_size_mb)

        # 2つのファイルに分割されることを確認
        assert len(result) == 2
        assert result[0] == Path("./large_file_001.tar.xz")
        assert result[1] == Path("./large_file_002.tar.xz")


def test_compress_files_small_files() -> None:
    """Test compress_files function with small files (no splitting)."""
    with (
        patch("tarfile.open", new_callable=MagicMock),
        patch("pathlib.Path.unlink") as mock_unlink,
        patch("pathlib.Path.rmdir") as mock_rmdir,
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.stat") as mock_stat,
    ):
        # 圧縮後のファイルサイズを70MBに設定, 制限80MB以下
        mock_stat.return_value.st_size = 70 * 1024 * 1024

        compress_files(Path("dummy_dst"), [Path("file1"), Path("file2")])

        # 元のファイルが削除されることを確認
        assert mock_unlink.call_count == 2
        mock_rmdir.assert_called_once()


def test_compress_files_large_files() -> None:
    """Test compress_files function with large files (requires splitting)."""
    with (
        patch("tarfile.open", new_callable=MagicMock),
        patch("pathlib.Path.unlink") as mock_unlink,
        patch("pathlib.Path.rmdir") as mock_rmdir,
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.stat") as mock_stat,
        patch("ffvqe.utils.file_operations.split_large_file") as mock_split,
    ):
        # 圧縮後のファイルサイズを160MBに設定, 制限80MBの2倍
        mock_stat.return_value.st_size = 160 * 1024 * 1024

        # split_large_file関数が2つの分割ファイルを返すようにモック
        mock_split.return_value = [
            Path("logs_archive_001.tar.xz"),
            Path("logs_archive_002.tar.xz"),
        ]

        compress_files(Path("dummy_dst"), [Path("file1"), Path("file2")])

        # split_large_file関数が呼び出されることを確認
        mock_split.assert_called_once()

        # 元のアーカイブファイルと元のファイルが削除されることを確認
        assert mock_unlink.call_count == 3  # 元のアーカイブ1つ + 元ファイル2つ
        mock_rmdir.assert_called_once()


def test_format_seconds() -> None:
    """Test format_seconds function."""
    result = format_seconds(3661)
    assert result == "00d, 01h01m01s"
