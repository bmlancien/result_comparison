
from collections import ChainMap
from flask import flash
from plotly import express as px
from plotly import graph_objects as go

from settings import COLUMN_JOINER, GRAPHS_DEFAULT_COLOR_MAP, GRAPHS_DEFAULT_LAYOUT, GRAPHS_DEFAULT_OPTIONS, \
    GRAPHS_MAX_TS_PER_PLOT


class PlottingError(Exception):
    """Thrown if plotting goes wrong"""


def get_empty_fig():
    empty_fig = px.bar()
    empty_fig.update_layout(GRAPHS_DEFAULT_LAYOUT)
    return empty_fig


def trim_timeseries(timeseries, max_entries=GRAPHS_MAX_TS_PER_PLOT):
    if len(timeseries.columns) > max_entries:
        flash(
            f"Too many timeseries to plot; only {max_entries} series are plotted.",
            category="warning",
        )
        timeseries = timeseries.loc[:, timeseries.columns[:max_entries]]
    return timeseries


def get_scalar_plot(data, options):
    if options["type"] == "bar":
        return bar_plot(data, options["options"])
    elif options["type"] == "radar":
        return radar_plot(data, options["options"])
    elif options["type"] == "dot":
        return dot_plot(data, options["options"])


def bar_plot(data, options):
    fig_options = ChainMap(options, GRAPHS_DEFAULT_OPTIONS["scalars"]["bar"].get_defaults())
    try:
        fig = px.bar(
            data,
            color_discrete_map=GRAPHS_DEFAULT_COLOR_MAP,
            labels={"source": "Simulation Framework"},
            **fig_options
        )
    except ValueError as ve:
        flash(f"Scalar plot error: {ve}", category="error")
        raise PlottingError(f"Scalar plot error: {ve}")
    fig.update_layout(GRAPHS_DEFAULT_LAYOUT)
    return fig


def radar_plot(data, options):
    categories = data[options["theta"]].unique()

    fig = go.Figure()
    for ellipse in data[options["color"]].unique():
        fig.add_trace(
            go.Scatterpolar(
                r=data[data[options["color"]] == ellipse][options["r"]],
                theta=categories,
                fill='toself',
                name=ellipse
            )
        )

    fig.update_layout(
        polar={
            "radialaxis": {
                "visible": True,
                "range": [data[options["r"]].min(), data[options["r"]].max()]
            }
        },
        showlegend=False
    )
    return fig


def dot_plot(data, options):
    y = data[options["y"]].unique()

    fig = go.Figure()

    for category in data[options["color"]].unique():
        cat_data = data[data[options["color"]] == category][options["x"]]
        fig.add_trace(go.Scatter(
            x=cat_data,
            y=y,
            name=category,
        ))
    fig.update_traces(mode='markers', marker=dict(line_width=1, symbol='circle', size=16))
    return fig


def get_timeseries_plot(data, options):
    if options["type"] == "line":
        return line_plot(data, options["options"])
    elif options["type"] == "box":
        return box_plot(data, options["options"])


def line_plot(data, options):
    fig_options = ChainMap(
        options,
        GRAPHS_DEFAULT_OPTIONS["timeseries"]["line"].get_defaults()
    )
    data = trim_timeseries(data)
    data.columns = [COLUMN_JOINER.join(map(str, column)) for column in data.columns]
    fig_options["y"] = [column for column in data.columns]
    try:
        fig = px.line(
            data.reset_index(),
            x="index",
            color_discrete_map=GRAPHS_DEFAULT_COLOR_MAP,
            **fig_options
        )
    except ValueError as ve:
        flash(f"Timeseries plot error: {ve}", category="error")
        raise PlottingError(f"Timeseries plot error: {ve}")
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector={
            "buttons": [
                {"count": 1, "label": "1d", "step": "day", "stepmode": "backward"},
                {"count": 7, "label": "1w", "step": "day", "stepmode": "backward"},
                {"count": 1, "label": "1m", "step": "month", "stepmode": "backward"},
                {"count": 6, "label": "6m", "step": "month", "stepmode": "backward"},
                {"step": "all"}
            ]
        }
    )
    fig.update_layout(GRAPHS_DEFAULT_LAYOUT)
    return fig


def box_plot(data, options):
    sample = options.pop("sample")
    fig_options = ChainMap(
        options,
        GRAPHS_DEFAULT_OPTIONS["timeseries"]["box"].get_defaults(exclude_non_plotly_options=True)
    )
    fig_options["x"] = "time"
    fig_options["y"] = "value"

    ts_resampled = data.resample(sample).sum()
    ts_resampled.index.name = "time"
    ts_unstacked = ts_resampled.unstack()
    ts_unstacked.name = "value"

    try:
        fig = px.box(
            ts_unstacked.reset_index(),
            notched=True,
            points="outliers",
            **fig_options
        )
    except ValueError as ve:
        flash(f"Timeseries plot error: {ve}", category="error")
        raise PlottingError(f"Timeseries plot error: {ve}")
    fig.update_layout(GRAPHS_DEFAULT_LAYOUT)
    return fig
