#!/usr/bin/env python3
"""Graph visualization for FFmpeg video quality evaluations."""

import argparse
import logging
import os
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from bokeh.core.property.container import Dict as BokehDict
from bokeh.core.property.container import List as BokehList
from bokeh.io import curdoc
from bokeh.layouts import column
from bokeh.layouts import row
from bokeh.models import ColumnDataSource
from bokeh.models import DataRange1d
from bokeh.models import FactorRange
from bokeh.models import LinearAxis
from bokeh.models import Range1d
from bokeh.models import RangeTool
from bokeh.models.widgets import MultiChoice
from bokeh.plotting import figure
import duckdb

from ffvqe.utils.yaml_handler import create_yaml_handler

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bokeh.models.sources import DataDict

# ロガーの設定
logger = logging.getLogger(__name__)


class DataTypeError(TypeError):
    """Custom exception for invalid data types.

    Raised when loaded data is not of the expected type.
    """

    def __init__(self, message: str = "Loaded data is not a dictionary") -> None:
        """Initialize the exception with a custom error message.

        Args:
            message: The error message to display.
        """
        super().__init__(message)


MyAny = Any


class GraphVisualizer:
    """Class for handling graph visualization for FFmpeg video quality evaluations."""

    def __init__(self) -> None:
        """Initialize the GraphVisualizer with default values."""
        self.yaml_parser = create_yaml_handler()
        self.source: ColumnDataSource | None = None
        self.x_shared: FactorRange | None = None
        self.size_plot: figure | None = None
        self.vmaf_plot: figure | None = None
        self.frame_plot: figure | None = None
        self.range_tool_plot: figure | None = None
        self.groupby_select: MultiChoice | None = None
        self.codec_filter: MultiChoice | None = None
        self.datafile: str = ""
        self.last_mod_time: float = 0

    @staticmethod
    def create_graph_argument_parser() -> argparse.ArgumentParser:
        """Create and configure the argument parser for graph visualization.

        Returns:
            Configured argument parser.
        """
        parser = argparse.ArgumentParser(
            description="FFmpeg video quality encoding quality evaluation for Graph.",
        )
        parser.add_argument(
            "--config",
            help="config file path. (e.g): ./videos/source/settings.yml",
            required=True,
            type=str,
        )
        return parser

    def load_data_with_duckdb(self, datafile: str) -> MyAny:
        """Load data using DuckDB.

        Args:
            datafile: Path to the JSON data file.

        Returns:
            DataFrame containing the loaded data.
        """
        con = duckdb.connect(database=":memory:")
        # パラメータ化されたクエリを使用
        con.execute("CREATE TABLE encodes AS SELECT * FROM read_json(?)", [datafile])
        query = """
        SELECT
            row_number() OVER () - 1                               AS index,
            codec                                                  AS codec,
            type                                                   AS type,
            preset                                                 AS preset,
            threads                                                AS threads,
            infile.name                                            AS ref_name,
            infile.type                                            AS ref_type,
            infile.option                                          AS infile_option,
            outfile.filename                                       AS outfile_filename,
            outfile.size_kbyte / 1000.0                            AS outfile_size_kbyte,
            outfile.bit_rate_kbs / 1000.0                          AS outfile_bit_rate_kbs,
            outfile.options                                        AS outfile_options,
            outfile.stream.gop                                     AS stream_gop,
            outfile.stream.has_b_frames                            AS stream_has_b_frames,
            outfile.stream.refs                                    AS stream_refs,
            outfile.stream.frames.I                                AS stream_frames_i,
            outfile.stream.frames.p                                AS stream_frames_p,
            outfile.stream.frames.b                                AS stream_frames_b,
            results.encode.second                                  AS enc_sec,
            results.encode.time                                    AS enc_time,
            results.compression_ratio_persent                      AS comp_ratio_persent,
            results.encode.speed                                   AS enc_speed,
            results.vmaf.pooled_metrics.float_ssim.min             AS ssim_min,
            results.vmaf.pooled_metrics.float_ssim.harmonic_mean   AS ssim_mean,
            results.vmaf.pooled_metrics.vmaf.min                   AS vmaf_min,
            results.vmaf.pooled_metrics.vmaf.harmonic_mean         AS vmaf_mean
        FROM encodes
        """
        data_df: MyAny = con.execute(query).df()
        con.close()

        return data_df

    def process_grouped_data(self, df: MyAny, selected_groups: BokehList) -> MyAny:
        """Group and aggregate the data based on selected groupby fields.

        Args:
            df: DataFrame containing the data.
            selected_groups: List of column names to group by.

        Returns:
            Grouped and aggregated DataFrame.
        """
        grouped: MyAny = (
            df.groupby(selected_groups)
            .agg(
                {
                    "outfile_bit_rate_kbs": "mean",
                    "outfile_size_kbyte": "mean",
                    "vmaf_mean": "mean",
                    "vmaf_min": "mean",
                    "stream_gop": "mean",
                    "stream_has_b_frames": "mean",
                    "stream_refs": "mean",
                    "stream_frames_i": "max",
                    "stream_frames_p": "max",
                    "stream_frames_b": "max",
                },
            )
            .reset_index()
        )

        # 複数のグループ化項目を文字列として結合
        grouped["group"] = grouped[selected_groups].astype(str).agg("_".join, axis=1)

        return grouped

    def update_source_and_factors(self, grouped: MyAny) -> None:
        """Update the ColumnDataSource and FactorRange with new grouped data.

        Args:
            grouped: Grouped and aggregated DataFrame.
        """
        if self.source is None or self.x_shared is None or self.size_plot is None:
            logger.error("Source, x_shared, or size_plot is not initialized")
            return

        new_data: DataDict = {
            "group": grouped["group"].tolist(),
            "outfile_bit_rate_kbs": grouped["outfile_bit_rate_kbs"].tolist(),
            "outfile_size_kbyte": grouped["outfile_size_kbyte"].tolist(),
            "vmaf_mean": grouped["vmaf_mean"].tolist(),
            "vmaf_min": grouped["vmaf_min"].tolist(),
            "stream_gop": grouped["stream_gop"].tolist(),
            "stream_has_b_frames": grouped["stream_has_b_frames"].tolist(),
            "stream_refs": grouped["stream_refs"].tolist(),
            "stream_frames_i": grouped["stream_frames_i"].tolist(),
            "stream_frames_p": grouped["stream_frames_p"].tolist(),
            "stream_frames_b": grouped["stream_frames_b"].tolist(),
        }

        self.source.data = new_data

        # x_range.factors を更新(ユニークなカテゴリのみ、ソート済み)
        self.x_shared.factors = cast("Sequence[str]", sorted(grouped["group"].unique()))

        # y_range を動的に更新
        if grouped["outfile_bit_rate_kbs"].tolist():
            max_bit_rate = max(grouped["outfile_bit_rate_kbs"])
        else:
            max_bit_rate = 1

        # Bokehの型定義の問題を回避するために型チェックを無視
        if hasattr(self.size_plot.extra_y_ranges["outfile_bit_rate_kbs"], "end"):
            self.size_plot.extra_y_ranges["outfile_bit_rate_kbs"].end = max_bit_rate * 1.1

    def refresh_data(self) -> None:
        """Refresh data based on current widget selections."""
        if self.groupby_select is None or self.codec_filter is None:
            logger.error("Widgets are not initialized")
            return

        try:
            updated_data = self.load_data_with_duckdb(self.datafile)
        except FileNotFoundError:
            logger.exception("File not found: %s", self.datafile)
            return

        # ウィジェットの選択に基づいてデータをフィルタリング
        selected_groups = self.groupby_select.value  # List[str]
        selected_codecs = self.codec_filter.value

        _df = updated_data.copy()
        if selected_codecs:
            _df = _df[_df["codec"].isin(selected_codecs)]

        grouped = self.process_grouped_data(_df, selected_groups)  # type: ignore[arg-type]
        self.update_source_and_factors(grouped)

    def update_data(self) -> None:
        """Update data if the YAML file has been modified."""
        try:
            current_mod_time = Path(self.datafile).stat().st_mtime
        except FileNotFoundError:
            # ファイルが存在しない場合の処理
            logger.exception("File not found: %s", self.datafile)
            return

        if current_mod_time > self.last_mod_time:
            sleep(5)
            logger.info("File updated: %s", self.datafile)

            # データを再ロード
            self.refresh_data()

            self.last_mod_time = current_mod_time
        else:
            logger.debug("No update needed; file has not changed.")

    def initialize_widgets(
        self,
        data: MyAny,
        selected_groups_initial: BokehList,
    ) -> tuple[MultiChoice, MultiChoice]:
        """Initialize widgets for the Bokeh application.

        Args:
            data: DataFrame containing the data.
            selected_groups_initial: Initial selection for group by widget.

        Returns:
            Tuple containing the groupby_select and codec_filter widgets.
        """
        # ウィジェットの定義
        groupby_select = MultiChoice(
            title="Group By",
            value=selected_groups_initial,  # type: ignore[arg-type]
            min_height=60,
            options=[
                "codec",
                "type",
                "preset",
                "threads",
                "ref_name",
                "ref_type",
                "infile_option",
                "outfile_options",
            ],
        )

        codec_options = sorted(set(data["codec"]))
        codec_filter = MultiChoice(
            title="Filter by Codec",
            min_height=60,
            value=codec_options,
            options=codec_options,
        )

        self.groupby_select = groupby_select
        self.codec_filter = codec_filter

        return groupby_select, codec_filter

    def create_plots(
        self,
        source: ColumnDataSource,
        x_shared: FactorRange,
        configfile: str,
        select_range: Range1d,
    ) -> tuple[figure, figure, figure, figure]:
        """Create plots for the Bokeh application.

        Args:
            source: Data source for the plots.
            x_shared: Shared x-range for the plots.
            configfile: Path to the configuration file.
            select_range: Range for the range tool.

        Returns:
            Tuple containing the size_plot, vmaf_plot, frame_plot, and range_tool_plot.
        """
        # プロットの作成
        size_plot = figure(  # type: ignore[call-arg]
            sizing_mode="stretch_both",
            min_width=400,
            min_height=300,
            title=f"Bit Rate (Mbs) and File Size (MB) from {configfile}",
            x_range=x_shared,
            y_range=DataRange1d(),
            x_axis_label="Group",
            y_axis_label="File Size (MB)",
            tooltips=[
                ("Group", "@group"),
                ("Bit Rate (Mbs)", "@outfile_bit_rate_kbs"),
                ("File Size(MB)", "@outfile_size_kbyte"),
                ("VMAF Mean", "@vmaf_mean"),
                ("VMAF Min", "@vmaf_min"),
            ],
        )

        # ファイルサイズの棒グラフ
        size_plot.vbar(
            x="group",
            top="outfile_size_kbyte",
            source=source,
            width=0.5,
            color="lightsteelblue",
            legend_label="File Size (MB)",
            selection_color="firebrick",
            nonselection_fill_alpha=0.6,
        )

        # 右側のy軸を追加
        size_plot.extra_y_ranges = cast(  # type: ignore[assignment]
            "BokehDict",
            {
                "outfile_bit_rate_kbs": Range1d(
                    start=0,
                    end=max(source.data["outfile_bit_rate_kbs"]) * 1.1
                    if source.data["outfile_bit_rate_kbs"]
                    else 1,
                ),
            },
        )

        size_plot.add_layout(
            LinearAxis(y_range_name="outfile_bit_rate_kbs", axis_label="Bit Rate (Mbs)"),
            "right",
        )

        # ビットレートの折れ線グラフ
        size_plot.line(
            "group",
            "outfile_bit_rate_kbs",
            source=source,
            line_width=2,
            color="red",
            y_range_name="outfile_bit_rate_kbs",
            legend_label="Bit Rate (Mbs)",
            selection_line_color="firebrick",
            nonselection_line_alpha=0.6,
        )
        size_plot.scatter(
            "group",
            "outfile_bit_rate_kbs",
            source=source,
            size=8,
            color="red",
            alpha=0.5,
            y_range_name="outfile_bit_rate_kbs",
            selection_color="firebrick",
            nonselection_alpha=0.6,
        )

        # VMAF プロットの作成
        vmaf_plot = figure(  # type: ignore[call-arg]
            sizing_mode="stretch_both",
            min_width=400,
            min_height=300,
            title=f"VMAF from {configfile}",
            x_range=x_shared,
            x_axis_label="Group",
            y_axis_label="VMAF Mean",
            tooltips=[
                ("Group", "@group"),
                ("VMAF min", "@vmaf_min"),
                ("VMAF mean", "@vmaf_mean"),
            ],
        )
        vmaf_plot.line(
            "group",
            "vmaf_mean",
            source=source,
            line_width=2,
            color="blue",
            selection_line_color="firebrick",
            nonselection_line_alpha=0.6,
        )
        vmaf_plot.line(
            "group",
            "vmaf_min",
            source=source,
            line_width=2,
            color="darkgray",
            selection_line_color="firebrick",
            nonselection_line_alpha=0.6,
        )
        vmaf_plot.scatter(
            "group",
            "vmaf_mean",
            source=source,
            size=8,
            color="green",
            alpha=0.5,
            selection_color="firebrick",
            nonselection_alpha=0.6,
        )

        # フレーム プロットの作成
        frame_plot = figure(  # type: ignore[call-arg]
            sizing_mode="stretch_both",
            min_width=400,
            min_height=300,
            title=f"Frames from {configfile}",
            x_range=x_shared,
            x_axis_label="Group",
            y_axis_label="Frame",
            tooltips=[
                ("Group", "@group"),
                ("GOP", "@stream_gop"),
                ("has_b", "@stream_has_b_frames"),
                ("refs", "@stream_refs"),
                ("I", "@stream_frames_i"),
                ("P", "@stream_frames_p"),
                ("B", "@stream_frames_b"),
            ],
        )

        # カテゴリカルなX軸の設定
        frame_plot.xgrid.grid_line_color = None  # type: ignore[attr-defined]

        # 積み上げ棒グラフの描画
        frame_plot.vbar_stack(
            stackers=["stream_frames_b", "stream_frames_p", "stream_frames_i"],
            x="group",
            width=0.6,
            color=["#718dbf", "#e84d60", "#c9d9d3"],
            source=source,
            legend_label=["B-Frame", "P-Frame", "I-Frame"],
        )

        # Create the RangeTool and link it to `x_shared`
        range_tool = RangeTool(x_range=x_shared)

        # RangeTool プロットの作成
        range_tool_plot = figure(  # type: ignore[call-arg]
            title="Select Range",
            sizing_mode="scale_width",
            height=20,
            tools="xpan",
            toolbar_location=None,
            x_range=select_range,
        )

        # Add a simplified view or summary to the range_tool_plot
        range_tool_plot.line(
            "group",
            "outfile_size_kbyte",
            source=source,
            color="lightsteelblue",
        )
        range_tool_plot.scatter(
            "group",
            "outfile_size_kbyte",
            source=source,
            color="lightsteelblue",
        )

        range_tool_plot.add_tools(range_tool)
        range_tool_plot.yaxis.visible = False  # type: ignore[attr-defined]
        range_tool_plot.xgrid.visible = False  # type: ignore[attr-defined]

        self.size_plot = size_plot
        self.vmaf_plot = vmaf_plot
        self.frame_plot = frame_plot
        self.range_tool_plot = range_tool_plot

        return size_plot, vmaf_plot, frame_plot, range_tool_plot

    def setup_layout_and_callbacks(self) -> None:
        """Set up the layout and callbacks for the Bokeh application."""
        if (
            self.groupby_select is None
            or self.codec_filter is None
            or self.size_plot is None
            or self.vmaf_plot is None
            or self.frame_plot is None
            or self.range_tool_plot is None
        ):
            logger.error("Widgets or plots are not initialized")
            return

        # ウィジェットにコールバックを追加
        def widget_callback(attr: str, old: list[Any], new: list[Any]) -> None:  # noqa: ARG001
            """Callback for widget value changes.

            Args:
                attr: The attribute that changed.
                old: The old value.
                new: The new value.
            """
            self.refresh_data()

        self.groupby_select.on_change("value", widget_callback)
        self.codec_filter.on_change("value", widget_callback)

        # レイアウトの組み立て
        layout = column(
            row(self.groupby_select, self.codec_filter),
            self.size_plot,
            self.vmaf_plot,
            self.frame_plot,
            self.range_tool_plot,
            sizing_mode="scale_width",
        )

        curdoc().add_root(layout)
        curdoc().title = "VQE from FFmpeg"

        # 周期的なデータ更新コールバックの設定
        curdoc().add_periodic_callback(
            self.update_data,
            10000,  # 10000 ミリ秒 ごとにチェック
        )

    def run(self, config_path: str) -> None:
        """Run the graph visualization application.

        Args:
            config_path: Path to the configuration file.
        """
        # 初期データの準備
        configfile = f"{config_path}"
        with Path(configfile).open("r") as file:
            __configs = self.yaml_parser.load(file)

        if not isinstance(__configs, dict):
            raise DataTypeError(message="Config file does not contain a dictionary.")

        self.datafile = __configs.get("configs", {}).get("datafile")
        if not isinstance(self.datafile, str):
            raise DataTypeError(message="datafile is not specified correctly in the config.")

        data = self.load_data_with_duckdb(self.datafile)

        # 文字列のリストをBokehListとして扱う
        selected_groups_initial = cast(
            "BokehList",
            [
                "codec",
                "type",
                "preset",
                "threads",
                "ref_type",
                "outfile_options",
            ],
        )
        grouped_initial = self.process_grouped_data(data, selected_groups_initial)
        self.source = ColumnDataSource(
            data={
                "group": grouped_initial["group"].tolist(),
                "outfile_bit_rate_kbs": grouped_initial["outfile_bit_rate_kbs"].tolist(),
                "outfile_size_kbyte": grouped_initial["outfile_size_kbyte"].tolist(),
                "vmaf_mean": grouped_initial["vmaf_mean"].tolist(),
                "vmaf_min": grouped_initial["vmaf_min"].tolist(),
                "stream_gop": grouped_initial["stream_gop"].tolist(),
                "stream_has_b_frames": grouped_initial["stream_has_b_frames"].tolist(),
                "stream_refs": grouped_initial["stream_refs"].tolist(),
                "stream_frames_i": grouped_initial["stream_frames_i"].tolist(),
                "stream_frames_p": grouped_initial["stream_frames_p"].tolist(),
                "stream_frames_b": grouped_initial["stream_frames_b"].tolist(),
            },
        )

        # 定義するx_rangeを FactorRange に変更(カテゴリカル軸用)
        self.x_shared = FactorRange(
            factors=sorted(grouped_initial["group"].unique()),
        )

        initial_window = max(10, len(self.source.data["group"]) - 1)
        select_range = Range1d(  # type: ignore[call-arg]
            start=0,
            end=initial_window,
            bounds="auto",
        )

        # ウィジェットの初期化
        self.initialize_widgets(data, selected_groups_initial)

        # プロットの作成
        self.create_plots(
            self.source,
            self.x_shared,
            configfile,
            select_range,
        )

        # レイアウトとコールバックの設定
        self.setup_layout_and_callbacks()

        # 最終更新時間の初期化
        self.last_mod_time = 0


def main() -> None:
    """Main entry point for the graph visualization.

    Initializes the Bokeh server application.
    """
    # コマンドライン引数のパース
    parser = GraphVisualizer.create_graph_argument_parser()
    args = parser.parse_args()

    # GraphVisualizerのインスタンスを作成して実行
    visualizer = GraphVisualizer()
    visualizer.run(args.config)


# テスト時でない場合のみ初期化を実行
is_testing = os.environ.get("PYTEST_RUNNING", "0") == "1"
if not is_testing:
    main()
