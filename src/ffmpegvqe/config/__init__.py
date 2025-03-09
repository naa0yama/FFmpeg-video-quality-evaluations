#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Configuration module for FFmpeg video quality evaluations."""

from ffmpegvqe.config.loader import load_config

__all__ = [
    "load_config",
]
