#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""duckdb."""

import argparse
from logging import INFO
from logging import getLogger
from pathlib import Path

import duckdb
import ruamel.yaml
from ruamel.yaml.representer import RoundTripRepresenter


class NoAliasDumper(RoundTripRepresenter):
    """ruamel.yaml custom class."""

    def ignore_aliases(self, data: object) -> bool:
        """Disabled alias."""
        return bool(data is not None)


logger = getLogger(__name__)
logger.setLevel(INFO)
yaml = ruamel.yaml.YAML(typ="safe", pure=True)
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.default_flow_style = False
yaml.explicit_start = True
yaml.width = 200
yaml.Representer = NoAliasDumper

parser = argparse.ArgumentParser(description="FFmpeg video quality encoding quality evaluation.")
parser.add_argument(
    "--config",
    help="config file path. (e.g): ./videos/h264_qsv-custom-la_icq.yml",
    required=True,
    type=str,
)


def load_config(config_path: str) -> str:
    """Load the configuration file and return the datafile path.

    Args:
        config_path (str): Path to the configuration file.

    Returns:
        str: Path to the datafile.
    """
    with Path(config_path).open("r") as file:
        return str(yaml.load(file)["configs"]["datafile"])


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


def main() -> None:
    """Main function to parse arguments and execute the workflow."""
    args = parser.parse_args()
    datafile = load_config(args.config)
    csvfile_type = datafile.replace(".json", "_gby_type.csv", 1)
    create_temp_table(csvfile_type)
    show_aggregated_results()


if __name__ == "__main__":
    main()
