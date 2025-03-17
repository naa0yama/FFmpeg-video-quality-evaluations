#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Tests for main module."""

import argparse
from unittest.mock import MagicMock
from unittest.mock import mock_open

import pytest
from pytest_mock import MockerFixture

from ffvqe.main import create_argument_parser
from ffvqe.main import main
from ffvqe.main import main_encode


def test_create_argument_parser() -> None:
    """Test argument parser creation."""
    parser = create_argument_parser()

    # パーサーが正しく作成されていることを確認
    assert isinstance(parser, argparse.ArgumentParser)

    # 必須引数が正しく設定されていることを確認
    # 注: _actionsは内部APIですが、テスト目的で使用しています
    required_args = {action.dest for action in parser._actions if action.required}  # noqa: SLF001
    assert "config" in required_args

    # オプション引数が正しく設定されていることを確認
    # 注: _actionsは内部APIですが、テスト目的で使用しています
    optional_args = {action.dest for action in parser._actions if not action.required}  # noqa: SLF001
    expected_optional_args = {
        "archive",
        "codec",
        "type",
        "overwrite",
        "encode",
        "ffmpeg_threads",
        "dist_save_video",
        "help",
    }
    assert expected_optional_args.issubset(optional_args)


@pytest.fixture
def mock_config() -> dict:
    """設定ファイルのモックデータを提供する。"""
    return {
        "configs": {
            "datafile": "/path/to/datafile.json",
        },
    }


@pytest.fixture
def mock_encode_cfg() -> list:
    """エンコード設定のモックデータを提供する。"""
    return [
        {
            "infile": {
                "filename": "/path/to/input.mp4",
            },
            "outfile": {
                "filename": "/path/to/output",
                "hash": "",  # 空のハッシュは処理が必要なことを示す
            },
        },
        {
            "infile": {
                "filename": "/path/to/input2.mp4",
            },
            "outfile": {
                "filename": "/path/to/output2",
                "hash": "existing_hash",  # 既存のハッシュは処理が不要なことを示す
            },
            "results": {
                "encode": {"second": 10},
                "probe": {"second": 5},
                "vmaf": {"second": 15},
            },
        },
    ]


@pytest.fixture
def mock_base_probe_log() -> dict:
    """ベースプローブログのモックデータを提供する。"""
    return {
        "format": {
            "duration": "60.0",
            "size": "7680000",
        },
    }


@pytest.fixture
def mock_probe_log() -> dict:
    """プローブログのモックデータを提供する。"""
    return {
        "format": {
            "duration": "60.0",
            "bit_rate": "1024000",
            "size": "7680000",
        },
    }


@pytest.fixture
def mock_vmaf_log() -> dict:
    """VMAFログのモックデータを提供する。"""
    return {
        "version": "1.0.0",
        "pooled_metrics": {
            "float_ssim": {
                "min": 0.9,
                "harmonic_mean": 0.95,
            },
            "vmaf": {
                "min": 85,
                "harmonic_mean": 90,
            },
        },
    }


@pytest.fixture
def mock_encode_response() -> dict:
    """エンコード応答のモックデータを提供する。"""
    return {
        "commandline": "ffmpeg -i input.mp4 -c:v libx264 output.mkv",
        "elapsed_time": 30.0,
        "elapsed_prbt": 5.0,
        "stream": {
            "gop": 12,
            "has_b_frames": 1,
            "refs": 3,
            "frames": {
                "I": 10,
                "P": 50,
                "B": 40,
                "total": 100,
            },
        },
    }


@pytest.fixture
def mock_vmaf_response() -> dict:
    """VMAF応答のモックデータを提供する。"""
    return {
        "commandline": "ffmpeg -i output.mkv -i input.mp4 -lavfi libvmaf output_vmaf.json",
        "elapsed_time": 15.0,
    }


def test_main_encode(  # noqa: PLR0913
    mocker: MockerFixture,
    mock_config: dict,
    mock_encode_cfg: list,
    mock_base_probe_log: dict,
    mock_probe_log: dict,
    mock_vmaf_log: dict,
    mock_encode_response: dict,
    mock_vmaf_response: dict,
) -> None:
    """Test main_encode function."""
    # ファイル操作のモック
    mock_file_open = mock_open()

    # json.loadの戻り値を設定
    mocker.patch(
        "json.load",
        side_effect=[
            mock_encode_cfg,  # 最初の呼び出し(datafile)
            mock_base_probe_log,  # 2番目の呼び出し(base_probe_log)
            mock_probe_log,  # 3番目の呼び出し(probe_log)
            mock_vmaf_log,  # 4番目の呼び出し(vmaf_log)
            mock_base_probe_log,  # 5番目の呼び出し(2回目のループでのbase_probe_log)
        ],
    )

    # json.dumpのモック
    mock_json_dump = mocker.patch("json.dump")

    # Path.openのモック
    mocker.patch("pathlib.Path.open", mock_file_open)

    # Path.existsのモック
    mocker.patch("pathlib.Path.exists", return_value=True)

    # Path.unlinkのモック
    mock_unlink = mocker.patch("pathlib.Path.unlink")

    # encodingとgetvmafのモック
    mock_encoding = mocker.patch("ffvqe.main.encoding", return_value=mock_encode_response)
    mock_getvmaf = mocker.patch("ffvqe.main.getvmaf", return_value=mock_vmaf_response)

    # getfilehashのモック
    mock_getfilehash = mocker.patch("ffvqe.main.getfilehash", return_value="new_hash")

    # fsyncのモック (使用されていないが、将来的に使用される可能性があるため残す)
    mocker.patch("ffvqe.main.fsync")

    # 引数の準備
    args = MagicMock()
    args.ffmpeg_threads = 4
    args.dist_save_video = False

    # 関数の実行
    main_encode(mock_config, args)

    # 検証
    assert mock_encoding.call_count == 1
    assert mock_getvmaf.call_count == 1
    assert mock_getfilehash.call_count == 1

    # ファイルが削除されたことを確認
    assert mock_unlink.call_count == 1

    # json.dumpが呼ばれたことを確認
    assert mock_json_dump.call_count == 1

    # エンコード設定が更新されたことを確認
    # 注: 実際のテストでは、mock_json_dumpの引数を検証することで
    # エンコード設定が正しく更新されたことを確認できます


def test_main_encode_with_exception(
    mocker: MockerFixture,
    mock_config: dict,
    mock_encode_cfg: list,
    mock_base_probe_log: dict,
) -> None:
    """Test main_encode function with exception."""
    # ファイル操作のモック
    mock_file_open = mock_open()

    # json.loadの戻り値を設定
    mocker.patch(
        "json.load",
        side_effect=[
            mock_encode_cfg,  # 最初の呼び出し(datafile)
            mock_base_probe_log,  # 2番目の呼び出し(base_probe_log)
        ],
    )

    # json.dumpのモック
    mock_json_dump = mocker.patch("json.dump")

    # Path.openのモック
    mocker.patch("pathlib.Path.open", mock_file_open)

    # Path.existsのモック
    mocker.patch("pathlib.Path.exists", return_value=True)

    # encodingが例外を発生させるようにモック (変数は使用されていないが、モックは必要)
    mocker.patch(
        "ffvqe.main.encoding",
        side_effect=Exception("Test exception"),
    )

    # fsyncのモック
    mock_fsync = mocker.patch("ffvqe.main.fsync")

    # 引数の準備
    args = MagicMock()
    args.ffmpeg_threads = 4

    # 関数の実行と例外の検証
    with pytest.raises(Exception, match="Test exception"):
        main_encode(mock_config, args)

    # 例外発生時にjson.dumpが呼ばれたことを確認
    assert mock_json_dump.call_count == 1
    assert mock_fsync.call_count == 1


def test_main_with_archive(mocker: MockerFixture) -> None:
    """Test main function with archive flag."""
    # コマンドライン引数のモック
    mock_args = MagicMock()
    mock_args.archive = True
    mock_args.encode = False
    mock_args.config = "dummy_config.yml"  # 実際には存在しないダミーのパス

    # argparseのモック
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=mock_args)

    # pathlib.Pathのモック
    # Pathクラスのコンストラクタをモック化して、実際のファイルシステム上のパスを作成しないようにする
    mock_path = mocker.patch("pathlib.Path")
    # Pathインスタンスのexistsメソッドをモック化して、常にFalseを返すようにする
    mock_path.return_value.exists.return_value = False

    # archiveのモック
    mock_archive = mocker.patch("ffvqe.main.archive")

    # load_configのモック
    mock_config = {"configs": {"datafile": "dummy_datafile.json"}}
    mocker.patch("ffvqe.main.load_config", return_value=mock_config)

    # sys.exitのモック
    mock_exit = mocker.patch("sys.exit")

    # 関数の実行
    main()

    # archiveが呼ばれたことを確認
    mock_archive.assert_called_once_with(config_path="dummy_config.yml", args=mock_args)

    # sys.exitが呼ばれていないことを確認
    mock_exit.assert_called_once_with("\n\n Archive done.")


def test_main_with_encode(mocker: MockerFixture) -> None:
    """Test main function with encode flag."""
    # コマンドライン引数のモック
    mock_args = MagicMock()
    mock_args.archive = False
    mock_args.encode = True
    mock_args.config = "/path/to/config.yml"

    # argparseのモック
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=mock_args)

    # load_configのモック
    mock_config = {"configs": {"datafile": "/path/to/datafile.json"}}
    mocker.patch("ffvqe.main.load_config", return_value=mock_config)

    # main_encodeのモック
    mock_main_encode = mocker.patch("ffvqe.main.main_encode")

    # getcsvのモック
    mock_getcsv = mocker.patch("ffvqe.main.getcsv")

    # 関数の実行
    main()

    # main_encodeが呼ばれたことを確認
    mock_main_encode.assert_called_once_with(config=mock_config, args=mock_args)

    # getcsvが呼ばれたことを確認
    mock_getcsv.assert_called_once_with(datafile="/path/to/datafile.json")


def test_main_with_both_flags(mocker: MockerFixture) -> None:
    """Test main function with both archive and encode flags."""
    # コマンドライン引数のモック
    mock_args = MagicMock()
    mock_args.archive = True
    mock_args.encode = True
    mock_args.config = "/path/to/config.yml"

    # argparseのモック
    mocker.patch("argparse.ArgumentParser.parse_args", return_value=mock_args)

    # archiveのモック
    mock_archive = mocker.patch("ffvqe.main.archive")

    # sys.exitのモック
    mock_exit = mocker.patch("sys.exit", side_effect=SystemExit)

    # 関数の実行と例外の検証
    with pytest.raises(SystemExit):
        main()

    # sys.exitが呼ばれたことを確認
    mock_exit.assert_called_once_with(
        "\n\nCannot be specified together with '--encode' and '--archive'.",
    )

    # archiveが呼ばれていないことを確認
    mock_archive.assert_not_called()
