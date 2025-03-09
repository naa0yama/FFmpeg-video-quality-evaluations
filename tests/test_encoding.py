#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Tests for encoding functions."""

import json
from unittest.mock import mock_open
from unittest.mock import patch

import pytest

from ffmpegvqe.encoding.encoder import encoding
from ffmpegvqe.encoding.encoder import get_versions
from ffmpegvqe.encoding.encoder import getprobe
from ffmpegvqe.encoding.encoder import getvmaf
from ffmpegvqe.encoding.frame_info import getframeinfo


@pytest.fixture
def mock_probe_log() -> dict:
    """Create a mock probe log for testing."""
    return {
        "frames": [
            {"pict_type": "I"},
            {"pict_type": "P"},
            {"pict_type": "B"},
            {"pict_type": "I"},
        ],
        "streams": [{"has_b_frames": 1, "refs": 1}],
    }


@pytest.fixture
def mock_encode_cfg() -> dict:
    """Create a mock encoding configuration for testing."""
    return {
        "hwaccels": "",
        "infile": {"option": "", "filename": "input.mp4"},
        "outfile": {"options": "", "filename": "output", "codec": "libx264", "preset": "medium"},
        "codec": "libx264",
        "preset": "medium",
    }


def test_getframeinfo(mock_probe_log: dict) -> None:
    """Test getframeinfo function."""
    with patch("pathlib.Path.open", mock_open(read_data=json.dumps(mock_probe_log))):
        result = getframeinfo("dummy_path")
        assert result["frames"]["I"] == 2
        assert result["frames"]["P"] == 1
        assert result["frames"]["B"] == 1
        assert result["gop"] == 1
        assert result["has_b_frames"] == 1
        assert result["refs"] == 1


def test_encoding(mock_encode_cfg: dict, mock_probe_log: dict) -> None:
    """Test encoding function."""
    with (
        patch("subprocess.Popen") as mock_popen,
        patch(
            "ffmpeg_progress_yield.FfmpegProgress.run_command_with_progress",
            return_value=[0, 50, 100],
        ),
        patch("pathlib.Path.open", mock_open(read_data=json.dumps(mock_probe_log))),
    ):
        mock_popen.return_value.poll.return_value = 0
        result = encoding(mock_encode_cfg, 10, 4)
        assert "commandline" in result
        assert "elapsed_time" in result
        assert "elapsed_prbt" in result
        assert "stream" in result


def test_getvmaf(mock_encode_cfg: dict) -> None:
    """Test getvmaf function."""
    with patch(
        "ffmpeg_progress_yield.FfmpegProgress.run_command_with_progress",
        return_value=[0, 50, 100],
    ):
        result = getvmaf(mock_encode_cfg, 4)
        assert "commandline" in result
        assert "elapsed_time" in result


def test_getprobe() -> None:
    """Test getprobe function."""
    with patch("subprocess.run") as mock_run:
        getprobe("dummy_video.mp4")
        mock_run.assert_called_once()


def test_get_versions() -> None:
    """Test get_versions function."""
    mock_versions_log = {
        "program_version": "n7.1",
        "library_versions": [{"name": "libavcodec", "ident": "Lavc61.19.100"}],
    }
    with (
        patch("subprocess.run"),
        patch("pathlib.Path.open", mock_open(read_data=json.dumps(mock_versions_log))),
        patch("pathlib.Path.unlink"),
    ):
        result = get_versions("dummy_config")
        assert result["ffmpege"]["program_version"] == "n7.1"
        assert result["ffmpege"]["library_versions"][0]["name"] == "libavcodec"
        assert result["ffmpege"]["library_versions"][0]["ident"] == "Lavc61.19.100"
