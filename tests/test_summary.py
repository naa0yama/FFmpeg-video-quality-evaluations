#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Test for summary."""

from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from ffvqe.summary import create_temp_table
from ffvqe.summary import show_aggregated_results


@pytest.fixture
def mock_yaml_data() -> dict:
    return {
        "configs": {
            "datafile": "test_data.json",
        },
    }


@pytest.fixture
def mock_csv_data(tmp_path: Path) -> str:
    csv_content = """ref_type,outfile_size_kbyte,outfile_bit_rate_kbs,enc_sec,comp_ratio_persent,ssim_mean,vmaf_min,vmaf_mean,outfile_options
type1,1000,2000,10,50,0.95,90,95,-test-option
type2,1500,3000,15,60,0.98,92,96,-other-option"""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)


def test_create_temp_table(mock_csv_data: str) -> None:
    with patch("duckdb.execute") as mock_execute:
        create_temp_table(mock_csv_data)
        mock_execute.assert_called_once()


def test_show_aggregated_results() -> None:
    with patch("duckdb.sql") as mock_sql:
        mock_sql.return_value = MagicMock()
        show_aggregated_results()
        assert mock_sql.call_count == 2
        assert mock_sql.return_value.show.call_count == 2
