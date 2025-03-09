#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Test CSV generation functionality."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from _pytest.capture import CaptureFixture
import pytest

from ffmpegvqe.data.csv_generator import getcsv


@pytest.fixture
def sample_json() -> str:
    """Provide a sample JSON file path."""
    return "tests/data/sample.json"


@pytest.fixture
def mock_json_data() -> Generator[MagicMock, None, None]:
    """Mock JSON data check."""
    with patch("ffmpegvqe.data.csv_generator.check_json_data", return_value=True) as mock:
        yield mock


@pytest.fixture
def mock_duckdb() -> Generator[MagicMock, None, None]:
    """Mock duckdb functionality."""
    with patch("ffmpegvqe.data.csv_generator.duckdb") as mock:
        # Setup mock connection and return values
        mock_connection = mock.connect.return_value
        mock_sql_result = mock_connection.sql.return_value
        mock_sql_result.write_csv = MagicMock()
        yield mock


@pytest.mark.usefixtures("mock_json_data")
def test_getcsv_file_naming(
    sample_json: str,
    mock_duckdb: MagicMock,
) -> None:
    """Test CSV file naming logic."""
    getcsv(sample_json, mock_duckdb.connect.return_value)

    # Verify SQL calls
    assert mock_duckdb.connect.return_value.sql.call_count == 3
    calls = mock_duckdb.connect.return_value.sql.call_args_list

    # Verify SQL queries
    assert calls[0][0][0].strip().startswith("SELECT")
    assert calls[1][0][0].strip().startswith("SELECT")
    assert calls[2][0][0].strip().startswith("SELECT")


@pytest.mark.usefixtures("mock_json_data")
def test_getcsv_creates_table(
    sample_json: str,
    mock_duckdb: MagicMock,
) -> None:
    """Test temporary table creation."""
    getcsv(sample_json, mock_duckdb.connect.return_value)

    mock_duckdb.connect.return_value.execute.assert_called_once()
    query = mock_duckdb.connect.return_value.execute.call_args[0][0]
    assert "CREATE TEMPORARY TABLE encodes" in query
    assert "FROM read_json" in query


@pytest.mark.usefixtures("mock_json_data")
def test_getcsv_prints_messages(
    sample_json: str,
    mock_duckdb: MagicMock,
    capsys: CaptureFixture,
) -> None:
    """Test console output messages."""
    getcsv(sample_json, mock_duckdb.connect.return_value)
    captured = capsys.readouterr()

    assert "[CSV   ] load" in captured.out
    assert "Export csv ....." in captured.out
    assert "Export csv done." in captured.out


@pytest.mark.usefixtures("mock_json_data")
def test_getcsv_generates_correct_filenames(
    sample_json: str,
    mock_duckdb: MagicMock,
) -> None:
    """Test generated CSV filenames."""
    getcsv(sample_json, mock_duckdb.connect.return_value)

    base = str(Path(sample_json).with_suffix(""))
    expected_files = [
        f"{base}_all.csv",
        f"{base}_gby_type.csv",
        f"{base}_gby_option.csv",
    ]

    # Verify write_csv calls were made with correct filenames
    mock_write_csv = mock_duckdb.connect.return_value.sql.return_value.write_csv
    assert mock_write_csv.call_count == 3

    # Check that each expected file was used in a write_csv call
    for expected_file in expected_files:
        mock_write_csv.assert_any_call(expected_file)
