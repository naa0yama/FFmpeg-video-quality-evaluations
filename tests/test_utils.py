#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Tests for utility functions."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch

from ffmpegvqe.utils.file_operations import compress_files
from ffmpegvqe.utils.file_operations import getfilehash
from ffmpegvqe.utils.time_format import format_seconds


def test_getfilehash() -> None:
    """Test getfilehash function."""
    with patch("pathlib.Path.open", mock_open(read_data=b"dummy content")):
        result = getfilehash("dummy_path")
        expected_hash = hashlib.sha256(b"dummy content").hexdigest()
        assert result == expected_hash


def test_compress_files() -> None:
    """Test compress_files function."""
    with (
        patch("tarfile.open", new_callable=MagicMock),
        patch("pathlib.Path.unlink") as mock_unlink,
        patch("pathlib.Path.rmdir") as mock_rmdir,
        patch("pathlib.Path.exists", return_value=True),
    ):
        compress_files(Path("dummy_dst"), [Path("file1"), Path("file2")])
        mock_unlink.assert_called()
        mock_rmdir.assert_called_once()


def test_format_seconds() -> None:
    """Test format_seconds function."""
    result = format_seconds(3661)
    assert result == "00d, 01h01m01s"
