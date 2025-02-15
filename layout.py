import uuid
import json
from collections import ChainMap

import dash_core_components as dcc
import dash_html_components as html
import dash_table

from graphs import get_empty_fig
from settings import (
    VERSION, SC_FILTERS, TS_FILTERS, UNITS, GRAPHS_DEFAULT_OPTIONS, GRAPHS_DEFAULT_COLOR_MAP, GRAPHS_DEFAULT_LABELS
)
from models import get_model_options, Filter, Colors, Labels


def get_header(app):
    return html.Div(
        children=[
            html.Div(
                children=[
                    html.Img(
                        src=app.get_asset_url("open_Modex-logo.png"),
                        style={"height": "100px", "width": "auto"},
                    ),
                    html.P(children=f"Version v{VERSION}"),
                    html.H4(children="Energy Frameworks to Germany"),
                    html.P(
                        children="How to efficiently sustain Germany's energy "
                        "\n usage with efficient parameters based on regions.",
                    ),
                ],
            ),
        ],
    )


def get_scenario_column(scenarios):
    return html.Div(
        style={"padding-bottom": "50px"},
        children=[
            html.Label("Select scenario:"),
            dcc.Dropdown(
                id="dd_scenario",
                multi=True,
                options=[
                    {
                        "label": f"{scenario['id']}, {scenario['scenario']}, {scenario['source']}",
                        "value": scenario["id"],
                    }
                    for scenario in scenarios
                ],
            ),
            html.Button("Reload", id="scenario_reload")
        ],
    )


def get_graph_options(data_type, graph_type, preset_options=None):
    preset_options = preset_options or {}
    chosen_options = ChainMap(preset_options, GRAPHS_DEFAULT_OPTIONS[data_type][graph_type].get_defaults())
    if data_type == "scalars":
        dd_options = [{"label": "value", "value": "value"}] + [
            {"label": filter_, "value": filter_} for filter_ in SC_FILTERS
        ]
    else:
        dd_options = [{"label": "series", "value": "series"}] + [
            {"label": filter_, "value": filter_} for filter_ in TS_FILTERS
        ]

    # sum concatenates lists:
    div = [dcc.Input(type="hidden", name="graph_type", value=graph_type)]
    for option, value in chosen_options.items():
        if GRAPHS_DEFAULT_OPTIONS[data_type][graph_type][option].from_filter:
            options = dd_options
        else:
            options = GRAPHS_DEFAULT_OPTIONS[data_type][graph_type][option].default
        component_type = GRAPHS_DEFAULT_OPTIONS[data_type][graph_type][option].type
        if component_type == "dropdown":
            component = dcc.Dropdown(
                id=f"{data_type}-{option}",
                options=options,
                value=value,
                clearable=GRAPHS_DEFAULT_OPTIONS[data_type][graph_type][option].clearable
            )
        elif component_type in ("input", "number"):
            component = dcc.Input(
                id=f"{data_type}-{option}",
                value=value,
                type="text" if component_type == "input" else "number"
            )
        else:
            raise ValueError("Unknown dcc component")
        div += [
            html.Label(GRAPHS_DEFAULT_OPTIONS[data_type][graph_type][option].label),
            component
        ]
    return div


def get_save_load_column(app):
    with app.server.app_context():
        options = get_model_options(Filter)
    return html.P(
        children=[
            html.P(id=f"save_load_errors", children=""),
            html.Label("Save filters as:"),
            dcc.Input(id="save_filters_name", type="text"),
            html.Button("Save", id="save_filters"),
            html.Label("Load filters"),
            dcc.Dropdown(
                id="load_filters",
                options=options,
                clearable=True
            )
        ]
    )


def get_aggregation_column():
    return html.Div(
        children=[
            html.P("Aggregation"),
            html.Label("Group-By:"),
            dcc.Dropdown(
                id="aggregation_group_by",
                multi=True,
                clearable=True,
                options=[{"label": filter_, "value": filter_} for filter_ in SC_FILTERS],
            )
        ]
    )


def get_units_column():
    return html.Div(
        id="units",
        children=sum(
            (
                [
                    html.Label(unit_name),
                    dcc.Dropdown(
                        options=[
                            {"label": unit, "value": unit}
                            for unit in unit_data["units"]
                        ],
                        value=unit_data["default"],
                        clearable=False,
                    ),
                ]
                for unit_name, unit_data in UNITS.items()
            ),
            [html.P("Units")],
        ),
    )


def get_filter_column():
    return html.Div(
        id="filters",
        children=sum(
            (
                [
                    html.Label(f"Filter {filter_.capitalize()}"),
                    dcc.Dropdown(
                        id=f"filter-{filter_}", multi=True, clearable=True
                    ),
                ]
                for filter_ in SC_FILTERS
            ),
            [],
        ),
    )


def get_color_column(app):
    with app.server.app_context():
        options = get_model_options(Colors)
    return html.Div(
        children=[
            html.Label(f"Color Map"),
            dcc.Textarea(
                id="colors", value=json.dumps(GRAPHS_DEFAULT_COLOR_MAP), style={"width": "100%", "height": "50px"}
            ),
            html.Label("Save colors as:"),
            dcc.Input(id="save_colors_name", type="text"),
            html.Button("Save", id="save_colors"),
            html.Label("Load colors"),
            dcc.Dropdown(
                id="load_colors",
                options=options,
                clearable=True
            ),
            html.P(id="colors_error", children="")
        ]
    )


def get_label_column(app):
    with app.server.app_context():
        options = get_model_options(Labels)
    return html.Div(
        children=[
            html.Label(f"Labels"),
            dcc.Textarea(
                id="labels", value=json.dumps(GRAPHS_DEFAULT_LABELS), style={"width": "100%", "height": "50px"}
            ),
            html.Label("Save labels as:"),
            dcc.Input(id="save_labels_name", type="text"),
            html.Button("Save", id="save_labels"),
            html.Label("Load labels"),
            dcc.Dropdown(
                id="load_labels",
                options=options,
                clearable=True
            ),
            html.P(id="labels_error", children="")
        ]
    )


def get_graph_column():
    return html.Div(
        style={"width": "68%", "display": "inline-block"},
        children=[
            html.Div(
                children=[
                    html.Div(
                        style={"width": "85%", "display": "inline-block", "vertical-align": "top"},
                        children=[
                            html.Button(f"Refresh {graph}", id=f"refresh_{graph}"),
                            dcc.Checklist(id=f"show_{graph}_data", options=[{"label": "Show Data", "value": "True"}]),
                            dcc.Loading(
                                style={"padding-bottom": "30px"},
                                type="default",
                                children=html.P(id=f"graph_{graph}_error", children="")
                            ),
                            dcc.Graph(
                                id=f"graph_{graph}",
                                figure=get_empty_fig(),
                                style={},
                                config={
                                    'toImageButtonOptions': {
                                        'format': 'svg',
                                    }
                                }
                            ),
                            dash_table.DataTable(
                                id=f"table_{graph}",
                                export_format="csv",
                                style_header={'backgroundColor': 'rgb(30, 30, 30)'},
                                style_cell={
                                    'backgroundColor': 'rgb(50, 50, 50)',
                                    'color': 'white'
                                },
                            )
                        ]
                    ),
                    html.Div(
                        style={"width": "15%", "display": "inline-block"},
                        children=[
                            dcc.RadioItems(
                                id=f"graph_{graph}_plot_switch",
                                options=[
                                    {"label": graph_type.capitalize(), "value": graph_type}
                                    for graph_type in GRAPHS_DEFAULT_OPTIONS[graph].keys()
                                ],
                                value=list(GRAPHS_DEFAULT_OPTIONS[graph].keys())[0]
                            ),
                            html.Div(
                                id=f"graph_{graph}_options",
                                children=get_graph_options(graph, list(GRAPHS_DEFAULT_OPTIONS[graph].keys())[0])
                            )
                        ]
                    ),
                ]
            )
            for graph in ("scalars", "timeseries")
        ],
    )


def get_layout(app, scenarios):
    session_id = str(uuid.uuid4())

    return html.Div(
        children=[
            html.Div(session_id, id="session-id", style={"display": "none"}),
            get_header(app),
            html.Div(
                children=[
                    get_scenario_column(scenarios),
                    html.Div(
                        children=[
                            html.Div(
                                style={"width": "30%", "display": "inline-block", "vertical-align": "top"},
                                children=[
                                    get_filter_column(),
                                    get_aggregation_column(),
                                    get_save_load_column(app),
                                    get_units_column(),
                                    get_color_column(app),
                                    get_label_column(app)
                                ]
                            ),
                            get_graph_column()
                        ]
                    ),
                ],
            ),
        ],
    )


def get_error_and_warnings_div(errors=None, warnings=None, infos=None):
    errors = errors or []
    warnings = warnings or []
    infos = infos or []
    return html.Div(
        children=(
            [html.P(error, style={"color": "red"}) for error in errors] +
            [html.P(warning, style={"color": "orange"}) for warning in warnings] +
            [html.P(info) for info in infos]
        )
    )
