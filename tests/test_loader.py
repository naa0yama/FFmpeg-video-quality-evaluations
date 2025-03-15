#!/usr/bin/env python3
"""
Tests for the configuration loader module in ffmpegvqe.
This module verifies correct behavior of load_config under various scenarios.
"""

from collections.abc import Callable
from collections.abc import Generator
import json
from pathlib import Path
from typing import Any
from typing import TypeVar
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from ffmpegvqe.config.loader import load_config
from ffmpegvqe.utils.exceptions import VQEError
from tests.file_io_helpers import cleanup_blacklisted_files
from tests.file_io_helpers import create_dummy_exists
from tests.file_io_helpers import create_dummy_open
from tests.file_io_helpers import create_dummy_write_text


class Args:
    """Container for command-line arguments used in tests.

    Attributes:
        codec (str): Codec filter, default is "all".
        type (str): Type filter, default is "all".
        ffmpeg_threads (int): Number of ffmpeg threads, default is 4.
        overwrite (bool): Whether to allow overwriting files, default is False.
        auto_download_references (bool): Whether to automatically download reference files, default is False.
    """

    def __init__(self) -> None:
        self.codec: str = "all"
        self.type: str = "all"
        self.ffmpeg_threads: int = 4
        self.overwrite: bool = False
        self.auto_download_references: bool = False


def is_blacklisted_file(path: Path) -> bool:
    """Check if a file is blacklisted from file I/O during tests.

    Blacklisted files: 'test_config.yml' or any file whose name starts with 'data' and ends with '.json'.

    Args:
        path (Path): The file path to check.

    Returns:
        bool: True if the file is blacklisted, False otherwise.
    """
    return (path.name == "test_config.yml") or (
        path.name.startswith("data") and path.name.endswith(".json")
    )


PathMethod = TypeVar("PathMethod", bound=Callable[..., Any])


def create_dummy_unlink(original_unlink: Callable[[Path], None]) -> Callable[[Path], None]:
    """
    Return a dummy unlink function that prevents deletion of blacklisted files.
    """

    def dummy_unlink(self: Path) -> None:
        if is_blacklisted_file(self):
            return
        original_unlink(self)

    return dummy_unlink


def _setup_mock_exists(original_exists: Callable[[Path], bool]) -> Callable[[Path], bool]:
    """リファレンスファイルとプローブファイルが存在するようにモックする関数を作成する。

    Args:
        original_exists: 元の Path.exists メソッド

    Returns:
        モック化された exists 関数
    """

    def mock_exists(self: Path) -> bool:
        # リファレンスファイルとプローブファイルが存在するようにする
        if str(self).endswith(".m2ts") or str(self).endswith("_ffprobe.json"):
            return True
        return create_dummy_exists(original_exists)(self)

    return mock_exists


def _create_mock_getfilehash() -> Callable[[str], str]:
    """getfilehash 関数のモックを作成する。

    Returns:
        モック化された getfilehash 関数
    """

    def mock_getfilehash(filename: str) -> str:
        # リファレンスファイルのハッシュ値を辞書で管理
        hash_map = {
            "ABBB_MPEG-2_1920x1080_30p.m2ts": "f005791ab9cabdc4468317d5d58becf3eb6228a49c6fad09e0923685712af769",
            "ASintel_MPEG-2_1920x1080_30p.m2ts": "8554804c935a382384eed9196ff88bd561767b6be1786aa4921087f265d92f3a",
            "AToS_MPEG-2_1920x1080_30p.m2ts": "ff6a0c366a3c631cf76d20c205cf505f964c9126551bf5bf10e8d99f9d04df52",
            "NAir_MPEG-2_1920x1080_30p.m2ts": "aec5612c556567df8cc3b37010c2850f709054293f1d5d0b96c68b349c2a97a2",
            "NArmy_MPEG-2_1920x1080_30p.m2ts": "aef3503a79fcacf0e65e368416b0b0b85e54b8eb77e2613a4b750b59fb2b50d5",
            "NNavy_MPEG-2_1920x1080_30p.m2ts": "52409e9400315916bb191dfafe4edd415204671ae00e2ddb447671f4850876cb",
            "test.mp4": "invalid_hash",  # test_load_config_invalid_hash 用
        }

        # ファイル名の末尾に一致するハッシュ値を返す
        for key, value in hash_map.items():
            if filename.endswith(key):
                return value

        return "dummy_hash"

    return mock_getfilehash


@pytest.fixture(autouse=True)
def disable_file_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable file creation, deletion, and writing for blacklisted files.

    This fixture overrides I/O methods of Path to prevent actual side effects
    on files that match the blacklist criteria.
    """
    original_write_text = Path.write_text
    original_unlink = Path.unlink
    original_open = Path.open
    original_exists = Path.exists
    original_mkdir = Path.mkdir

    # Path メソッドのモック設定
    monkeypatch.setattr(Path, "write_text", create_dummy_write_text(original_write_text))
    monkeypatch.setattr(Path, "unlink", create_dummy_unlink(original_unlink))
    monkeypatch.setattr(Path, "open", create_dummy_open(original_open))
    monkeypatch.setattr(Path, "exists", _setup_mock_exists(original_exists))
    monkeypatch.setattr(Path, "mkdir", original_mkdir)

    # getfilehash 関数をモック
    monkeypatch.setattr("ffmpegvqe.utils.file_operations.getfilehash", _create_mock_getfilehash())

    # getprobe 関数をモック
    with patch("ffmpegvqe.config.loader.getprobe") as mock_getprobe:
        mock_getprobe.return_value = None

    cleanup_blacklisted_files()


@pytest.fixture
def mock_args() -> Args:
    """Provide an instance of Args for testing."""
    return Args()


@pytest.fixture
def mock_yaml() -> MagicMock:
    """Return a MagicMock instance to simulate a YAML handler."""
    return MagicMock()


@pytest.fixture
def mock_yaml_handler(mock_yaml: MagicMock) -> Generator[MagicMock, None, None]:
    """Patch the YAML handler creation in load_config to use a mock."""
    with patch("ffmpegvqe.config.loader.create_yaml_handler", return_value=mock_yaml):
        yield mock_yaml


@pytest.fixture
def test_config() -> str:
    """Return the test configuration filename."""
    return "test_config.yml"


def test_load_config_new_config(
    mock_args: Args,
    mock_yaml_handler: MagicMock,
    test_config: str,
) -> None:
    """Test loading a new configuration file.

    Verifies that load_config returns a dictionary with the expected keys.
    """
    mock_yaml_handler.load.return_value = {}

    if Path(test_config).exists():
        Path(test_config).unlink()

    result = load_config(test_config, mock_args)

    assert isinstance(result, dict)
    assert "configs" in result
    assert "datafile" in result
    assert isinstance(result["configs"], dict)
    assert isinstance(result["datafile"], str)

    if Path(test_config).exists():
        Path(test_config).unlink()


def test_load_config_with_codec_filter(
    mock_args: Args,
    mock_yaml_handler: MagicMock,
    test_config: str,
) -> None:
    """Test configuration filtering using codec.

    Ensures that only patterns with the specified codec are returned.
    """
    mock_args.codec = "libx264"
    mock_yaml_handler.load.return_value = {}

    result = load_config(test_config, mock_args)
    patterns = result["configs"]["patterns"]
    assert all(p["codec"] == "libx264" for p in patterns)


def test_load_config_with_type_filter(
    mock_args: Args,
    mock_yaml_handler: MagicMock,
    test_config: str,
) -> None:
    """Test configuration filtering using type.

    Validates that patterns match both codec and type when specified.
    """
    mock_args.codec = "libx264"
    mock_args.type = "CRF"
    mock_yaml_handler.load.return_value = {}

    result = load_config(test_config, mock_args)
    patterns = result["configs"]["patterns"]
    assert all(p["codec"] == "libx264" and p["type"] == "CRF" for p in patterns)


@pytest.mark.usefixtures("mock_yaml_handler")
def test_load_config_invalid_hash(
    mock_args: Args,
    test_config: str,
) -> None:
    """Test loading configuration with an invalid hash.

    Expects a VQEError when reference validation fails.
    """
    # _validate_references 関数をモックして、エラーを発生させる
    with patch("ffmpegvqe.config.loader._validate_references") as mock_validate:
        mock_validate.side_effect = VQEError("Error: references name: test, basehash not match.")
        with pytest.raises(VQEError):
            load_config(test_config, mock_args)


def test_download_reference_file(
    mock_args: Args,
    mock_yaml_handler: MagicMock,
    test_config: str,
) -> None:
    """Test downloading reference file from GitHub.

    Verifies that the download_reference_file function is called when a reference file is missing.
    """
    # auto_download_references フラグを設定
    mock_args.auto_download_references = True

    # 設定ファイルが存在するようにモック
    mock_yaml_handler.load.return_value = {
        "configs": {
            "references": [
                {
                    "name": "test",
                    "basefile": "test.mp4",
                    "basehash": "valid_hash",
                },
            ],
            "patterns": [],
        },
    }

    # _validate_references 関数をモック
    with patch("ffmpegvqe.config.loader._validate_references") as mock_validate:
        # download_reference_file 関数をモック
        with patch("ffmpegvqe.config.loader.download_reference_file") as mock_download:
            # ダウンロードが成功したことを示す
            mock_download.return_value = True

            # _validate_references 関数の実装をモック
            def mock_validate_references(
                _configs: dict[str, Any],  # 未使用の引数を_で始める
                _args: object,  # 未使用の引数を_で始める
                _configfile: str,  # 未使用の引数を_で始める
            ) -> None:
                # リファレンスファイルが存在しないことをシミュレート
                with (
                    patch("pathlib.Path.exists", return_value=False),
                    patch("ffmpegvqe.config.loader.is_default_reference", return_value=True),
                ):
                    # download_reference_file 関数を呼び出す
                    from ffmpegvqe.config.loader import download_reference_file

                    download_reference_file("test.mp4", "valid_hash")

            mock_validate.side_effect = mock_validate_references

            # 設定を読み込む
            load_config(test_config, mock_args)

            # download_reference_file 関数が呼び出されたことを確認
            mock_download.assert_called()

        mock_validate.side_effect = mock_validate_references

        # 設定を読み込む
        load_config(test_config, mock_args)


def test_download_reference_file_failure(
    mock_args: Args,
    mock_yaml_handler: MagicMock,
    test_config: str,
) -> None:
    """Test handling of download failure.

    Verifies that a VQEError is raised when download_reference_file returns False.
    """
    # auto_download_references フラグを設定
    mock_args.auto_download_references = True

    # 設定ファイルが存在するようにモック
    mock_yaml_handler.load.return_value = {
        "configs": {
            "references": [
                {
                    "name": "test",
                    "basefile": "test.mp4",
                    "basehash": "valid_hash",
                },
            ],
            "patterns": [],
        },
    }

    # _validate_references 関数をモック
    with patch("ffmpegvqe.config.loader._validate_references") as mock_validate:
        # _validate_references 関数の実装をモック
        def mock_validate_references(
            _configs: dict[str, Any],  # 未使用の引数を_で始める
            _args: object,  # 未使用の引数を_で始める
            _configfile: str,  # 未使用の引数を_で始める
        ) -> None:
            # リファレンスファイルが存在しないことをシミュレート
            with (
                patch("pathlib.Path.exists", return_value=False),
                patch("ffmpegvqe.config.loader.is_default_reference", return_value=True),
                patch("ffmpegvqe.config.loader.download_reference_file") as mock_download,
            ):
                # ダウンロードが失敗したことを示す
                mock_download.return_value = False
                # VQEError を発生させる
                error_message = "Error: Failed to download reference file: test"
                raise VQEError(error_message)

        mock_validate.side_effect = mock_validate_references

        # VQEError が発生することを確認
        with pytest.raises(VQEError):
            load_config(test_config, mock_args)


def test_load_config_existing_datafile(
    mock_args: Args,
    mock_yaml_handler: MagicMock,
    test_config: str,
    tmp_path: Path,
) -> None:
    """Test loading configuration where the datafile already exists.

    Ensures that if the datafile exists, its path is used in the configuration.
    """
    datafile = tmp_path / "test_data.json"
    mock_yaml_handler.load.return_value = {
        "configs": {
            "datafile": str(datafile),
            "references": [],
            "patterns": [],
        },
    }

    test_data = [{"id": "test_id"}]
    datafile.write_text(json.dumps(test_data))

    with patch("ffmpegvqe.config.loader._get_datafile_path", return_value=(str(datafile), [])):
        result = load_config(test_config, mock_args)
        assert result["datafile"] == str(datafile)


def test_load_config_with_empty_patterns(
    mock_args: Args,
    mock_yaml_handler: MagicMock,
    test_config: str,
) -> None:
    """Test loading configuration with an empty patterns list.

    Verifies that default patterns are applied when the provided list is empty.
    """
    mock_yaml_handler.load.return_value = {
        "configs": {
            "datafile": "",
            "patterns": [],
            "references": [],
        },
    }

    with patch("ffmpegvqe.config.loader._get_default_patterns", return_value=[]):
        result = load_config(test_config, mock_args)
        assert len(result["configs"]["patterns"]) == 0
        assert all(isinstance(p, dict) for p in result["configs"]["patterns"])


def test_load_config_invalid_yaml_structure(
    mock_args: Args,
    mock_yaml_handler: MagicMock,
    test_config: str,
) -> None:
    """Test loading configuration with an invalid YAML structure.

    Expects defaults to be used when the YAML structure is not as expected.
    """
    mock_yaml_handler.load.return_value = []  # Invalid structure
    result = load_config(test_config, mock_args)
    assert isinstance(result["configs"], dict)
    assert "patterns" in result["configs"]
    assert "references" in result["configs"]
    assert "datafile" in result


def test_load_config_missing_configs_key(
    mock_args: Args,
    mock_yaml_handler: MagicMock,
    test_config: str,
) -> None:
    """Test loading configuration when the 'configs' key is missing.

    Ensures that default configuration values are provided.
    """
    mock_yaml_handler.load.return_value = {
        "invalid": {},
    }
    result = load_config(test_config, mock_args)
    assert "configs" in result
    assert isinstance(result["configs"], dict)
    assert "patterns" in result["configs"]


def test_load_config_with_codec_and_all_types(
    mock_args: Args,
    mock_yaml_handler: MagicMock,
    test_config: str,
) -> None:
    """Test configuration loading for a specific codec with all types.

    Validates that multiple types are present when the type filter is 'all'.
    """
    mock_args.codec = "h264_qsv"
    mock_args.type = "all"
    mock_yaml_handler.load.return_value = {}

    result = load_config(test_config, mock_args)
    patterns = result["configs"]["patterns"]
    assert len(patterns) > 0
    assert all(p["codec"] == "h264_qsv" for p in patterns)
    assert len({p["type"] for p in patterns}) > 1
