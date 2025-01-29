#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""graph."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any
from typing import cast

from bokeh.core.property.container import Dict as BokehDict
from bokeh.io import curdoc
from bokeh.layouts import column
from bokeh.models import ColumnDataSource
from bokeh.models import HoverTool
from bokeh.models import LinearAxis
from bokeh.models import Range1d
from bokeh.plotting import figure
import ruamel.yaml

# データソースを作成
yaml = ruamel.yaml.YAML(typ="safe", pure=True)
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.default_flow_style = False
yaml.explicit_start = True
yaml.width = 99


class DataTypeError(TypeError):
    """Custom exception for invalid data types."""

    def __init__(self, message: str = "Loaded data is not a dictionary") -> None:
        """Init."""
        super().__init__(message)


def load_data(yaml_file_path: str) -> dict[str, Any]:
    """Load data."""
    with Path(yaml_file_path).open("r", encoding="utf-8") as file:
        _data = yaml.load(file)
        if not isinstance(_data, dict):
            raise DataTypeError
        return _data


# データの抽出
def extract_data(data: dict[str, Any]) -> dict[str, Sequence[Any]]:
    """Extract data."""
    bit_rate = [(encode["outfile"]["bit_rate_kbs"] / 1000) for encode in data["encodes"]]
    options = [encode["outfile"]["options"] for encode in data["encodes"]]
    size_kbyte = [(encode["outfile"]["size_byte"] / 1024 / 1024) for encode in data["encodes"]]
    codec = [encode["codec"] for encode in data["encodes"]]
    type_ = [encode["type"] for encode in data["encodes"]]
    vmaf_meam = [
        encode["results"]["vmaf"]
        .get("pooled_metrics", {})
        .get("vmaf", {})
        .get("harmonic_mean", 0.0)
        for encode in data["encodes"]
    ]
    index = list(range(len(bit_rate)))  # x 軸の値はインデックス
    return {
        "index": index,
        "bit_rate": bit_rate,
        "size_kbyte": size_kbyte,
        "codec": codec,
        "type": type_,
        "options": options,
        "vmaf_meam": vmaf_meam,
    }


# 初期データの準備
yaml_file_path = "videos/source/settings.yml"
data = load_data(yaml_file_path)
source = ColumnDataSource(data=extract_data(data))

# プロットの作成
size_plot = figure(
    sizing_mode="scale_both",
    min_width=400,
    min_height=300,
    title="Bit Rate (Mbs) and File Size (MB) Plot",
    x_axis_label="Index",
    y_axis_label="File Size (MB)",
)

# ファイルサイズの棒グラフ
size_plot.vbar(
    x="index",
    top="size_kbyte",
    source=source,
    width=0.5,
    color="lightsteelblue",
    legend_label="File Size (MB)",
)

# 右側のy軸を追加
size_plot.extra_y_ranges = cast(
    BokehDict,
    {
        "bit_rate": Range1d(start=0, end=max(source.data["bit_rate"]) * 1.1),
    },
)
size_plot.add_layout(LinearAxis(y_range_name="bit_rate", axis_label="Bit Rate (Mbs)"), "right")


# ビットレートの折れ線グラフ
size_plot.line(
    "index",
    "bit_rate",
    source=source,
    line_width=2,
    color="red",
    y_range_name="bit_rate",
    legend_label="Bit Rate (Mbs)",
)
size_plot.scatter(
    "index",
    "bit_rate",
    source=source,
    size=8,
    color="red",
    alpha=0.5,
    y_range_name="bit_rate",
)


# VMAF プロットの作成
vmaf_plot = figure(
    sizing_mode="scale_both",
    min_width=400,
    min_height=100,
    title="VMAF",
    x_axis_label="Index",
    y_axis_label="vmaf_meam",
)
vmaf_plot.line("index", "vmaf_meam", source=source, line_width=2, color="blue")
vmaf_plot.scatter("index", "vmaf_meam", source=source, size=8, color="green", alpha=0.5)

# ツールチップの設定
size_plot.add_tools(
    HoverTool(
        tooltips=[
            ("Index", "@index"),
            ("Bit Rate (Mbs)", "@bit_rate"),
            ("File Size(MB)", "@size_kbyte"),
            ("Codec", "@codec"),
            ("Type", "@type"),
            ("Options", "@options"),
        ],
    ),
)
vmaf_plot.add_tools(
    HoverTool(
        tooltips=[
            ("Index", "@index"),
            ("VMAF", "@vmaf_meam"),
            ("Codec", "@codec"),
            ("Type", "@type"),
            ("Options", "@options"),
        ],
    ),
)

# レイアウトの作成
layout = column(size_plot, vmaf_plot, sizing_mode="scale_both")

# ドキュメントにレイアウトを追加
curdoc().add_root(layout)
curdoc().title = "VQE from FFmpeg"


def update_data() -> None:
    """Update data."""
    _new_data = load_data(yaml_file_path)
    source.data = cast(dict[str, Any], extract_data(_new_data))


curdoc().add_periodic_callback(
    update_data(),  # type: ignore[func-returns-value]
    5000,
)  # 5000 ミリ秒 ごとにチェック
