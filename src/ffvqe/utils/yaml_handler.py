#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""YAML handling utilities for FFmpeg video quality evaluations."""

from typing import Any

from ruamel.yaml import YAML  # 明示的にYAMLクラスをインポート

# Import RoundTripRepresenter with proper type annotation
from ruamel.yaml.representer import RoundTripRepresenter


class NoAliasDumper(RoundTripRepresenter):
    """Custom YAML dumper that ignores aliases.

    This class extends RoundTripRepresenter to disable YAML aliases,
    ensuring each object is serialized independently.
    """

    def ignore_aliases(self, data: Any) -> bool:  # noqa: ARG002, ANN401
        """Disable YAML aliases.

        Args:
            data: The data being serialized.

        Returns:
            Always returns True to disable aliases.
        """
        return True


def create_yaml_handler() -> YAML:
    """Create a configured YAML handler.

    Returns:
        A configured YAML instance with custom settings.
    """
    yaml = YAML(typ="safe", pure=True)  # インポートしたYAMLクラスを使用
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.default_flow_style = False
    yaml.explicit_start = True
    yaml.width = 200
    yaml.Representer = NoAliasDumper
    return yaml
