#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Time formatting utilities for FFmpeg video quality evaluations."""

from time import gmtime
from time import strftime


def format_seconds(seconds: int) -> str:
    """Format seconds to days, hours, minutes, and seconds.

    Args:
        seconds: Number of seconds to format.

    Returns:
        A formatted string in the format "DDd, HHhMMmSSs".
    """
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{days:02d}d, {hours:02d}h{minutes:02d}m{secs:02d}s"


def format_time_hms(seconds: float) -> str:
    """Format seconds to hours, minutes, and seconds using strftime.

    Args:
        seconds: Number of seconds to format.

    Returns:
        A formatted string in the format "HH:MM:SS".
    """
    return strftime("%H:%M:%S", gmtime(seconds))
