#!/usr/bin/env python3
# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
"""graph."""

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
from time import sleep
from typing import Any
from typing import cast

from bokeh.core.property.container import Dict as BokehDict
from bokeh.io import curdoc
from bokeh.layouts import column
from bokeh.models import ColumnDataSource
from bokeh.models import LinearAxis
from bokeh.models import Range1d
from bokeh.models import RangeTool
from bokeh.plotting import figure
import ruamel.yaml

# データソースを作成
yaml = ruamel.yaml.YAML(typ="safe", pure=True)
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.default_flow_style = False
yaml.explicit_start = True
yaml.width = 200


class DataTypeError(TypeError):
    """Custom exception for invalid data types."""

    def __init__(self, message: str = "Loaded data is not a dictionary") -> None:
        """Init."""
        super().__init__(message)


parser = argparse.ArgumentParser(
    description="FFmpeg video quality encoding quality evaluation for Graph.",
)
parser.add_argument(
    "--config",
    help="config file path.",
    default="./videos/source/settings.yml",
)
args = parser.parse_args()


def load_data(datafile: str) -> dict[str, Any]:
    """Load data."""
    with Path(datafile).open("r") as file:
        _data = json.load(file)

    if not isinstance(_data, dict):
        raise DataTypeError
    return _data


# データの抽出
def extract_data(data: dict[str, Any]) -> dict[str, Sequence[Any]]:
    """Extract data."""
    _bit_rate: list = []
    _options: list = []
    _size_mbyte: list = []
    _codec: list = []
    _type: list = []
    _vmaf_min: list = []
    _vmaf_mean: list = []
    _stream_gop: list = []
    _stream_has_b_frames: list = []
    _stream_refs: list = []
    _stream_frames_i: list = []
    _stream_frames_p: list = []
    _stream_frames_b: list = []

    for __encode in data["encodes"]:
        _bit_rate.append(__encode["outfile"].get("bit_rate_kbs", 0.0) / 1000)
        _options.append(__encode["outfile"]["options"])
        _size_mbyte.append(__encode["outfile"].get("size_kbyte", 0.0) / 1024)
        _codec.append(__encode["codec"])
        _type.append(__encode["type"])
        _vmaf_min.append(
            __encode["results"]
            .get("vmaf", {})
            .get("pooled_metrics", {})
            .get("vmaf", {})
            .get("min", 0.0),
        )
        _vmaf_mean.append(
            __encode["results"]
            .get("vmaf", {})
            .get("pooled_metrics", {})
            .get("vmaf", {})
            .get("harmonic_mean", 0.0),
        )
        _stream_gop.append(__encode["outfile"].get("stream", {}).get("gop", 0))
        _stream_has_b_frames.append(__encode["outfile"].get("stream", {}).get("has_b_frames", 0))
        _stream_refs.append(__encode["outfile"].get("stream", {}).get("refs", 0))

        _stream_frames_i.append(
            __encode["outfile"].get("stream", {}).get("frames", {}).get("I", 0),
        )
        _stream_frames_p.append(
            __encode["outfile"].get("stream", {}).get("frames", {}).get("P", 0),
        )
        _stream_frames_b.append(
            __encode["outfile"].get("stream", {}).get("frames", {}).get("B", 0),
        )

    index = list(range(len(_bit_rate)))  # x 軸の値はインデックス
    print(f"\n\nload index {_bit_rate.index(0.0) if 0.0 in _bit_rate else len(index)}.")  # noqa: T201
    return {
        "index": index,
        "bit_rate": _bit_rate,
        "size_mbyte": _size_mbyte,
        "codec": _codec,
        "type": _type,
        "options": _options,
        "vmaf_min": _vmaf_min,
        "vmaf_mean": _vmaf_mean,
        "stream_gop": _stream_gop,
        "stream_has_b_frames": _stream_has_b_frames,
        "stream_refs": _stream_refs,
        "stream_frames_i": _stream_frames_i,
        "stream_frames_p": _stream_frames_p,
        "stream_frames_b": _stream_frames_b,
    }


# 初期データの準備
configfile = f"{args.config}"
with Path(configfile).open("r") as file:
    __configs = yaml.load(file)
datafile: str = f"{__configs['configs']['datafile']}"

data = load_data(datafile)
source = ColumnDataSource(data=extract_data(data))

# 定義するx_rangeを共有するために作成
x_shared = Range1d(
    start=0,
    end=len(source.data["index"]),
    bounds="auto",
)

initial_window = max(10, len(source.data["index"]) - 1)
select_range = Range1d(
    start=0,
    end=initial_window,
    bounds="auto",
)
# プロットの作成
size_plot = figure(
    sizing_mode="scale_both",
    min_width=400,
    min_height=300,
    title="Bit Rate (Mbs) and File Size (MB)",
    x_range=x_shared,
    x_axis_label="Index",
    y_axis_label="File Size (MB)",
    tooltips=[
        ("Index", "@index"),
        ("Bit Rate (Mbs)", "@bit_rate"),
        ("File Size(MB)", "@size_mbyte"),
        ("Codec", "@codec"),
        ("Type", "@type"),
        ("Options", "@options"),
    ],
)

# ファイルサイズの棒グラフ
size_plot.vbar(
    x="index",
    top="size_mbyte",
    source=source,
    width=0.5,
    color="lightsteelblue",
    legend_label="File Size (MB)",
    selection_color="firebrick",
    nonselection_fill_alpha=0.6,
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
    selection_line_color="firebrick",
    nonselection_line_alpha=0.6,
)
size_plot.scatter(
    "index",
    "bit_rate",
    source=source,
    size=8,
    color="red",
    alpha=0.5,
    y_range_name="bit_rate",
    selection_color="firebrick",
    nonselection_alpha=0.6,
)

# VMAF プロットの作成
vmaf_plot = figure(
    sizing_mode="scale_both",
    min_width=400,
    min_height=300,
    title="VMAF",
    x_range=x_shared,
    x_axis_label="Index",
    y_axis_label="VMAF Mean",
    tooltips=[
        ("Index", "@index"),
        ("VMAF min", "@vmaf_min"),
        ("VMAF mean", "@vmaf_mean"),
        ("Codec", "@codec"),
        ("Type", "@type"),
        ("Options", "@options"),
    ],
)

vmaf_plot.line(
    "index",
    "vmaf_mean",
    source=source,
    line_width=2,
    color="blue",
    selection_line_color="firebrick",
    nonselection_line_alpha=0.6,
)
vmaf_plot.line(
    "index",
    "vmaf_min",
    source=source,
    line_width=2,
    color="darkgray",
    selection_line_color="firebrick",
    nonselection_line_alpha=0.6,
)
vmaf_plot.scatter(
    "index",
    "vmaf_mean",
    source=source,
    size=8,
    color="green",
    alpha=0.5,
    selection_color="firebrick",
    nonselection_alpha=0.6,
)


# フレーム プロットの作成
frame_plot = figure(
    sizing_mode="scale_both",
    min_width=400,
    min_height=300,
    title="Frames",
    x_range=x_shared,
    x_axis_label="Index",
    y_axis_label="Frame",
    tooltips=[
        ("Index", "@index"),
        ("GOP", "@stream_gop"),
        ("has_b", "@stream_has_b_frames"),
        ("refs", "@stream_refs"),
        ("I", "@stream_frames_i"),
        ("P", "@stream_frames_p"),
        ("B", "@stream_frames_b"),
        ("Codec", "@codec"),
        ("Type", "@type"),
        ("Options", "@options"),
    ],
)

# カテゴリカルなX軸の設定
frame_plot.xgrid.grid_line_color = None

# 積み上げ棒グラフの描画
frame_plot.vbar_stack(
    stackers=["stream_frames_b", "stream_frames_p", "stream_frames_i"],
    x="index",
    width=0.6,
    color=["#718dbf", "#e84d60", "#c9d9d3"],
    source=source,
    legend_label=["B-Frame", "P-Frame", "I-Frame"],
)  # type: ignore[no-untyped-call]


# Create the RangeTool and link it to `x_shared`
range_tool = RangeTool(x_range=x_shared)

# RangeTool プロットの作成
range_tool_plot = figure(
    title="Select Range",
    sizing_mode="scale_width",
    height=50,
    tools="xpan",
    toolbar_location=None,
    x_range=select_range,
)

# Add a simplified view or summary to the range_tool_plot
range_tool_plot.line("index", "size_mbyte", source=source, color="lightsteelblue")
range_tool_plot.scatter("index", "size_mbyte", source=source, size=5, color="lightsteelblue")

range_tool_plot.add_tools(range_tool)

range_tool_plot.yaxis.visible = False
range_tool_plot.xgrid.visible = False

# Assemble the layout
layout = column(
    size_plot,
    frame_plot,
    vmaf_plot,
    range_tool_plot,
    sizing_mode="scale_width",
)

curdoc().add_root(layout)
curdoc().title = "VQE from FFmpeg"

last_mod_time: float = 0


def update_data() -> None:
    """Update data if the YAML file has been modified."""
    global last_mod_time  # noqa: PLW0603
    try:
        current_mod_time = Path(datafile).stat().st_mtime
    except FileNotFoundError:
        # Handle the case where the file does not exist
        print(f"File not found: {datafile}")  # noqa: T201
        return

    if current_mod_time > last_mod_time:
        sleep(15)
        _new_data = load_data(datafile)
        source.data = cast(dict[str, Any], extract_data(_new_data))
        last_mod_time = current_mod_time
        print(f"Data updated at {current_mod_time}")  # noqa: T201
    else:
        print("No update needed; file has not changed.")  # noqa: T201


curdoc().add_periodic_callback(
    update_data,
    15000,
)  # 15000 ミリ秒 ごとにチェック
