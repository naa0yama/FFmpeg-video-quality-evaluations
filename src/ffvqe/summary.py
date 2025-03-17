#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""duckdb."""

from logging import INFO
from logging import StreamHandler
from logging import getLogger
from pathlib import Path
from typing import Any

import duckdb

from ffvqe.config.loader import load_config

logger = getLogger(__name__)
logger.setLevel(INFO)

handler = StreamHandler()
handler.setLevel(INFO)
logger.addHandler(handler)


def create_temp_table(csvfile_type: str) -> None:
    """Create a temporary table in DuckDB from the CSV file.

    Args:
        csvfile_type (str): Path to the CSV file.
    """
    logger.info("[CSV] loading %s", csvfile_type)
    duckdb.execute(
        """
            CREATE TEMPORARY TABLE encodes AS
            SELECT *
            FROM read_csv(?)
        """,
        [csvfile_type],
    )


def show_aggregated_results() -> None:
    """Show aggregated results for entries with VMAF mean greater than or equal to 93.00."""
    duckdb.sql(
        """
        SELECT
            ref_type,
            ROUND(AVG(outfile_size_kbyte), 3)        AS outfile_size_kbyte,
            ROUND(AVG(outfile_bit_rate_kbs), 3)      AS outfile_bit_rate_kbs,
            ROUND(AVG(enc_sec), 3)                   AS enc_sec,
            ROUND(AVG(comp_ratio_persent), 3)        AS comp_ratio_persent,
            ROUND(AVG(ssim_mean), 3)                 AS ssim_mean,
            ROUND(AVG(vmaf_min), 3)                  AS vmaf_min,
            ROUND(AVG(vmaf_mean), 3)                 AS vmaf_mean,
            outfile_options
        FROM encodes
        GROUP BY ref_type, outfile_options
        ORDER BY outfile_options DESC
        LIMIT 8
    """,
    ).show()

    duckdb.sql(
        """
        SELECT
            codec,
            ROUND(AVG(outfile_size_kbyte), 3)        AS outfile_size_kbyte,
            ROUND(AVG(outfile_bit_rate_kbs), 3)      AS outfile_bit_rate_kbs,
            ROUND(AVG(enc_sec), 3)                   AS enc_sec,
            ROUND(AVG(comp_ratio_persent), 3)        AS comp_ratio_persent,
            ROUND(AVG(ssim_mean), 3)                 AS ssim_mean,
            ROUND(AVG(vmaf_min), 3)                  AS vmaf_min,
            ROUND(AVG(vmaf_mean), 3)                 AS vmaf_mean,
            ROUND(AVG((200 - (vmaf_min + vmaf_mean)) +
                (2 - (ssim_mean + comp_ratio_persent))), 3) AS pt,
            ROUND(AVG(gop), 3)                       AS gop,
            IF(AVG(has_b_frames) > 1,
                ROUND(AVG(has_b_frames) + 1, 3), 0)  AS bf,
            ROUND(AVG(refs), 3)                      AS refs,
            CONCAT(ROUND(AVG(FI), 3), ' / ',
                ROUND(AVG(FP), 3), ' / ',
                ROUND(AVG(FB), 3))                   AS "I/P/B frames",
            outfile_options,
        FROM encodes
        WHERE
            comp_ratio_persent >= 0.60 AND
            ssim_mean >= 0.99 AND
            vmaf_mean >= 93.00 AND
            vmaf_mean <= 100.00
        GROUP BY codec, outfile_options
        ORDER BY pt DESC
        """,
    ).show()


def main(config_path: str, args: object) -> None:
    """Main function to parse arguments and execute the workflow."""
    __configs: dict[str, Any] = load_config(configfile=config_path, args=args)
    __datafile: Path = Path(f"{__configs['configs']['datafile']}")
    csvfile_type: str = f"{__datafile}".replace(".json", "_gby_type.csv")
    create_temp_table(csvfile_type)
    show_aggregated_results()
