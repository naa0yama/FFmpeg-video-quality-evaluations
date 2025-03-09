#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Exception classes for FFmpeg video quality evaluations."""


class VQEError(Exception):
    """Base exception class for VQE errors.

    This class serves as the base for all custom exceptions in the VQE package.
    """

    def __init__(self, message: str) -> None:
        """Initialize the exception with a custom error message.

        Args:
            message: The error message to display.
        """
        super().__init__(f"Error: {message}")
