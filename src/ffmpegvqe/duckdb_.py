#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""entrypoint."""

import duckdb

duckdb.sql(
    r"""
    SELECT
        data.codec                                                  AS codec,
        data.type                                                   AS type,
        data.preset                                                 AS preset,
        data.threads                                                AS threads,
        data.infile.name                                            AS ref_name,
        data.infile.type                                            AS ref_type,
        data.outfile.filename                                       AS "outfile_filename",
        data.outfile.size_kbyte                                     AS "outfile_size_kbyte",
        data.outfile.bit_rate_kbs                                   AS "outfile_bit_rate_kbs",
        data.outfile.options                                        AS "outfile_options",
        data.results.encode.second                                  AS "enc_sec",
        data.results.encode.time                                    AS "enc_time",
        data.results.compression_ratio_persent                      AS "comp_ratio_persent",
        data.results.encode.speed                                   AS "enc_speed",
        data.results.vmaf.pooled_metrics.float_ssim.min             AS "ssim_min",
        data.results.vmaf.pooled_metrics.float_ssim.harmonic_mean   AS "ssim_mean",
        data.results.vmaf.pooled_metrics.vmaf.min                   AS "vmaf_min",
        data.results.vmaf.pooled_metrics.vmaf.harmonic_mean         AS "vmaf_mean",

    FROM read_json_auto('videos/databe4973df8c0f.json') AS data
    LIMIT 5;
    """,
).write_csv("out.csv")

""" codec, size で VMAF を集計
SELECT
    ANY_VALUE(codec),
    ANY_VALUE(size),
    AVG(vmaf_mean) AS vmaf_mean
FROM 'videos/data.csv'
WHERE
        codec NOT LIKE 'rawvideo'
GROUP BY codec, size
ORDER BY vmaf_mean DESC
"""

""" size 別の VMAF を集計
SELECT
    ANY_VALUE(size),
    AVG(vmaf_mean) AS vmaf_mean
FROM 'videos/data.csv'
WHERE
    codec NOT LIKE 'rawvideo'
GROUP BY size
ORDER BY vmaf_mean DESC
"""
