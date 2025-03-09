#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""Pytest configuration."""

# Standard Library
from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).parent.parent / "src"))


@pytest.fixture(autouse=True)
def setup_test_env() -> None:
    """Set up test environment."""
    return
