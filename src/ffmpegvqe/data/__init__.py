#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Data processing module for FFmpeg video quality evaluations."""

from ffmpegvqe.data.archive import archive
from ffmpegvqe.data.csv_generator import getcsv

__all__ = [
    "archive",
    "getcsv",
]
