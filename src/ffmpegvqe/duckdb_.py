#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""entrypoint."""

import argparse

import duckdb

parser = argparse.ArgumentParser(description="FFmpeg video quality encoding quality evaluation.")
parser.add_argument(
    "--csv",
    help="config file path. (e.g): ./videos/data6ded9efe21da_gby_type.csv",
    required=True,
    type=str,
)
parser.add_argument(
    "--option",
    help="option (e.g): -global_quality 35",
    required=True,
    type=str,
)
args = parser.parse_args()


print(f"[CSV   ] load {args.csv} ....")  # noqa: T201
duckdb.execute(
    f"""
        CREATE TEMPORARY TABLE encodes AS
        SELECT *
        FROM read_csv('{args.csv}')
    """,  # noqa: S608
)

duckdb.sql(
    f"""
    SELECT
        ref_type,
        ROUND(outfile_size_kbyte, 2),
        ROUND(outfile_bit_rate_kbs, 2),
        ROUND(enc_sec, 2),
        ROUND(comp_ratio_persent, 2),
        ROUND(ssim_mean, 2),
        CONCAT(ROUND(vmaf_min, 2), ' / ', ROUND(vmaf_mean, 2)),
        outfile_options,
    FROM encodes
    WHERE
        outfile_options like '%{args.option}%'
    """,
).show()

duckdb.sql(
    r"""
    SELECT
        ref_type,
        ROUND(outfile_size_kbyte, 2),
        ROUND(outfile_bit_rate_kbs, 2),
        ROUND(enc_sec, 2),
        ROUND(comp_ratio_persent, 2),
        ROUND(ssim_mean, 2),
        CONCAT(ROUND(vmaf_min, 2), ' / ', ROUND(vmaf_mean, 2)),
        outfile_options,
    FROM encodes
    WHERE
        vmaf_mean >= 93.00 AND
        ref_type == 'Anime'
    ORDER BY outfile_options DESC
    LIMIT 6
    """,
).show()

duckdb.sql(
    r"""
    SELECT
        ref_type,
        ROUND(outfile_size_kbyte, 2),
        ROUND(outfile_bit_rate_kbs, 2),
        ROUND(enc_sec, 2),
        ROUND(comp_ratio_persent, 2),
        ROUND(ssim_mean, 2),
        CONCAT(ROUND(vmaf_min, 2), ' / ', ROUND(vmaf_mean, 2)),
        outfile_options,
    FROM encodes
    WHERE
        vmaf_mean >= 93.00 AND
        ref_type == 'Nature'
    ORDER BY outfile_options DESC
    LIMIT 6
    """,
).show()
