#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""VSCode extensions utilities."""

import json
from pathlib import Path
import re
from typing import cast


def get_vscode_extensions(filepath: str | None = None) -> list[str]:
    """Get VSCode extensions from extensions.json file.

    Args:
        filepath: Path to extensions.json file. If None, use default path.

    Returns:
        List of extension IDs.

    Raises:
        FileNotFoundError: If file does not exist.
        json.JSONDecodeError: If file is not valid JSON.
    """
    if filepath is None:
        filepath = f"{Path(__file__).parent.parent.parent.parent}/.vscode/extensions.json"

    if not Path(filepath).exists():
        error_message = f"File not found: {filepath}"
        raise FileNotFoundError(error_message)

    with Path(filepath).open(encoding="utf-8") as f:
        content = f.read()
        if not content:
            return []

    # Remove comments from JSONC
    content_without_comments = re.sub(r"/\*[\s\S]*?\*/|//.*", "", content)

    try:
        data = json.loads(content_without_comments)
    except json.JSONDecodeError as err:
        error_message = "Invalid JSON"
        raise json.JSONDecodeError(error_message, content, 0) from err

    if not isinstance(data, dict) or "recommendations" not in data:
        return []

    recommendations = data.get("recommendations", [])
    if not isinstance(recommendations, list):
        return []

    # 明示的に型をキャストして、mypyに型情報を提供
    return cast(list[str], [str(item) for item in recommendations if isinstance(item, str)])
