#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""test_vscode_extensions."""

# Standard Library
import json
from pathlib import Path
import re


# %%
def load_jsonc(filepath: str, encoding: str = "utf-8") -> dict:
    """Load jsonc."""
    with Path(filepath).open(encoding=encoding) as f:
        text = f.read()
    text_without_comment = re.sub(r"/\*[\s\S]*?\*/|//.*", "", text)
    json_obj: dict = json.loads(text_without_comment)
    return json_obj


# %%
def test_vscode_extensions_sync() -> None:
    """Test vscode extensions sync."""
    vscode_dict = load_jsonc(
        filepath=f"{Path(__file__).parent.parent}/.vscode/extensions.json",
    )

    devcontainer_dict = load_jsonc(
        filepath=f"{Path(__file__).parent.parent}/.devcontainer/devcontainer.json",
    )

    assert (
        vscode_dict["recommendations"]
        == devcontainer_dict["customizations"]["vscode"]["extensions"]
    )


# %%
