#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""CSV generation functionality for FFmpeg video quality evaluations."""

import json
from pathlib import Path
import sys

import duckdb


def check_json_data(datafile: str) -> bool:
    """Check if JSON data file exists and contains data.

    Args:
        datafile: Path to the JSON data file.

    Returns:
        True if file exists and contains data, False otherwise.
    """
    data: list[dict] = []
    try:
        with Path(f"{datafile}").open("r") as file:
            data = json.load(file)
    except FileNotFoundError:
        return False

    return data != []


def create_duckdb_connection() -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection.

    Returns:
        A DuckDB connection object.
    """
    return duckdb.connect(database=":memory:")


def create_temporary_table(connection: duckdb.DuckDBPyConnection, datafile: str) -> None:
    """Create a temporary table from JSON data.

    Args:
        connection: DuckDB connection object.
        datafile: Path to the JSON data file.
    """
    connection.execute(
        f"""
            CREATE TEMPORARY TABLE encodes AS
            SELECT *
            FROM read_json('{datafile}')
        """,  # noqa: S608
    )


def getcsv(datafile: str, db_connection: duckdb.DuckDBPyConnection | None = None) -> None:
    """Generate CSV files from JSON data.

    Processes the JSON data file and generates three CSV files:
    - _all.csv: Contains all data points
    - _gby_type.csv: Data grouped by reference type
    - _gby_option.csv: Data grouped by encoding options

    Args:
        datafile: Path to the JSON data file.
        db_connection: Optional DuckDB connection for testing.
    """
    if not check_json_data(datafile):
        sys.exit("\n\n[CSV   ] No data found in the JSON file.\n")

    print(f"[CSV   ] load {datafile} ....")  # noqa: T201

    # Create a temporary table from the JSON data
    con = db_connection if db_connection else create_duckdb_connection()
    create_temporary_table(con, datafile)

    # Generate CSV files if data exists
    __csvfile_all: str = f"{datafile}".replace(".json", "_all.csv", 1)
    __csvfile_type: str = f"{datafile}".replace(".json", "_gby_type.csv", 1)
    __csvfile_option: str = f"{datafile}".replace(".json", "_gby_option.csv", 1)

    print("Export csv .....")  # noqa: T201

    # Generate all data CSV
    all_query = r"""
        SELECT
            row_number() OVER () - 1                               AS index,
            codec                                                  AS codec,
            type                                                   AS type,
            preset                                                 AS preset,
            threads                                                AS threads,
            outfile.stream.gop                                     AS gop,
            outfile.stream.has_b_frames                            AS has_b_frames,
            outfile.stream.refs                                    AS refs,
            outfile.stream.frames.I                                AS fI,
            outfile.stream.frames.P                                AS fP,
            outfile.stream.frames.B                                AS fB,
            outfile.stream.frames.total                            AS fT,
            infile.name                                            AS ref_name,
            infile.type                                            AS ref_type,
            infile.option                                          AS infile_option,
            outfile.filename                                       AS outfile_filename,
            outfile.size_kbyte                                     AS outfile_size_kbyte,
            outfile.bit_rate_kbs                                   AS outfile_bit_rate_kbs,
            outfile.options                                        AS outfile_options,
            results.encode.second                                  AS enc_sec,
            results.encode.time                                    AS enc_time,
            results.compression_ratio_persent                      AS comp_ratio_persent,
            results.encode.speed                                   AS enc_speed,
            results.vmaf.pooled_metrics.float_ssim.min             AS ssim_min,
            results.vmaf.pooled_metrics.float_ssim.harmonic_mean   AS ssim_mean,
            results.vmaf.pooled_metrics.vmaf.min                   AS vmaf_min,
            results.vmaf.pooled_metrics.vmaf.harmonic_mean         AS vmaf_mean
        FROM encodes
    """
    con.sql(all_query).write_csv(__csvfile_all)

    # Generate type grouped CSV
    type_query = r"""
        SELECT
            row_number() OVER () - 1                                   AS index,
            codec                                                      AS codec,
            type                                                       AS type,
            preset                                                     AS preset,
            threads                                                    AS threads,
            MAX(outfile.stream.gop)                                    AS gop,
            MAX(outfile.stream.has_b_frames)                           AS has_b_frames,
            MAX(outfile.stream.refs)                                   AS refs,
            MAX(outfile.stream.frames.I)                               AS fI,
            MAX(outfile.stream.frames.P)                               AS fP,
            MAX(outfile.stream.frames.B)                               AS fB,
            MAX(outfile.stream.frames.total)                           AS fT,
            infile.type                                                AS ref_type,
            AVG(outfile.size_kbyte)                                    AS outfile_size_kbyte,
            AVG(outfile.bit_rate_kbs)                                  AS outfile_bit_rate_kbs,
            outfile.options                                            AS outfile_options,
            AVG(results.encode.second)                                 AS enc_sec,
            AVG(results.compression_ratio_persent)                     AS comp_ratio_persent,
            AVG(results.encode.speed)                                  AS enc_speed,
            AVG(results.vmaf.pooled_metrics.float_ssim.min)            AS ssim_min,
            AVG(results.vmaf.pooled_metrics.float_ssim.harmonic_mean)  AS ssim_mean,
            AVG(results.vmaf.pooled_metrics.vmaf.min)                  AS vmaf_min,
            AVG(results.vmaf.pooled_metrics.vmaf.harmonic_mean)        AS vmaf_mean
        FROM encodes
        GROUP BY codec, type, preset, threads, ref_type, outfile_options
    """
    con.sql(type_query).write_csv(__csvfile_type)

    # Generate option grouped CSV
    option_query = r"""
        SELECT
            row_number() OVER () - 1                                   AS index,
            codec                                                      AS codec,
            type                                                       AS type,
            preset                                                     AS preset,
            threads                                                    AS threads,
            MAX(outfile.stream.gop)                                    AS gop,
            MAX(outfile.stream.has_b_frames)                           AS has_b_frames,
            MAX(outfile.stream.refs)                                   AS refs,
            MAX(outfile.stream.frames.I)                               AS fI,
            MAX(outfile.stream.frames.P)                               AS fP,
            MAX(outfile.stream.frames.B)                               AS fB,
            MAX(outfile.stream.frames.total)                           AS fT,
            AVG(outfile.size_kbyte)                                    AS outfile_size_kbyte,
            AVG(outfile.bit_rate_kbs)                                  AS outfile_bit_rate_kbs,
            outfile.options                                            AS outfile_options,
            AVG(results.encode.second)                                 AS enc_sec,
            AVG(results.compression_ratio_persent)                     AS comp_ratio_persent,
            AVG(results.encode.speed)                                  AS enc_speed,
            AVG(results.vmaf.pooled_metrics.float_ssim.min)            AS ssim_min,
            AVG(results.vmaf.pooled_metrics.float_ssim.harmonic_mean)  AS ssim_mean,
            AVG(results.vmaf.pooled_metrics.vmaf.min)                  AS vmaf_min,
            AVG(results.vmaf.pooled_metrics.vmaf.harmonic_mean)        AS vmaf_mean
        FROM encodes
        GROUP BY codec, type, preset, threads, outfile_options
    """
    con.sql(option_query).write_csv(__csvfile_option)

    print("Export csv done.")  # noqa: T201
