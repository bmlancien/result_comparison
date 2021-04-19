import pathlib

import urllib3

import dash
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
from flask import get_flashed_messages
from flask_caching import Cache

from data import dev
import preprocessing
from layout import get_layout, get_graph_options, get_error_and_warnings_div
from settings import SECRET_KEY, DEBUG, SKIP_TS, FILTERS, TS_FILTERS, GRAPHS_DEFAULT_OPTIONS, USE_DUMMY_DATA, CACHE_CONFIG
import scenario
import graphs

urllib3.disable_warnings()

APP_PATH = str(pathlib.Path(__file__).parent.resolve())

# Initialize app
app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=4.0"},
    ],
)
app.layout = get_layout(app, scenarios=scenario.get_scenarios())
server = app.server
server.secret_key = SECRET_KEY

# Cache
cache = Cache()
cache.init_app(server, config=CACHE_CONFIG)


@cache.memoize()
def get_scenario_data(scenario_id):
    if USE_DUMMY_DATA:
        return dev.get_dummy_data()
    return scenario.get_scenario_data(scenario_id)


@cache.memoize()
def get_multiple_scenario_data(*scenario_ids):
    scenarios = [
        get_scenario_data(scenario_id) for scenario_id in scenario_ids
    ]
    return scenario.merge_scenario_data(scenarios)


@app.callback(
    Output(component_id="dd_scenario", component_property="options"),
    Input('scenario_reload', 'n_clicks'),
)
def reload_scenarios(_):
    scenarios = scenario.get_scenarios()
    options = [
        {
            "label": f"{sc['id']}, {sc['scenario']}, {sc['source']}",
            "value": sc["id"],
        }
        for sc in scenarios
    ]
    return options


@app.callback(
    [Output(component_id=f"filter_{filter_}", component_property="options") for filter_ in FILTERS],
    [Input(component_id="dd_scenario", component_property="value")],
)
def load_scenario(scenarios):
    if scenarios is None:
        raise PreventUpdate
    scenarios = scenarios if isinstance(scenarios, list) else [scenarios]
    data = get_multiple_scenario_data(*scenarios)
    return preprocessing.get_filter_options(data)


@app.callback(
    [Output(component_id=f"graph_scalars_options", component_property="children")],
    [Input(component_id="graph_scalars_plot_switch", component_property="value")],
)
def toggle_scalar_graph_options(plot_type):
    return get_graph_options("scalars", plot_type),


@app.callback(
    [Output(component_id=f"graph_timeseries_options", component_property="children")],
    [Input(component_id="graph_timeseries_plot_switch", component_property="value")],
)
def toggle_timeseries_graph_options(plot_type):
    return get_graph_options("timeseries", plot_type),



@app.callback(
    [
        Output(component_id='graph_scalars', component_property='figure'),
        Output(component_id='graph_scalars_error', component_property='children'),    ],
    [
        Input(component_id="dd_scenario", component_property="value"),
        Input(component_id="aggregation_group_by", component_property="value"),
        Input(component_id="graph_scalars_options_switch", component_property="value"),
    ] +
    [Input(component_id=f"filter_{filter_}", component_property='value') for filter_ in FILTERS] +
    [
        Input(component_id=f"graph_scalars_option_{option}", component_property='value')
        for option in GRAPHS_DEFAULT_OPTIONS["scalars"]
    ]
)
def scalar_graph(scenarios, agg_group_by, use_custom_graph_options, *filter_args):
    if scenarios is None:
        raise PreventUpdate
    data = get_multiple_scenario_data(*scenarios)
    filters, graph_options = preprocessing.extract_filters_and_options("scalars", filter_args, use_custom_graph_options)
    try:
        preprocessed_data = preprocessing.prepare_scalars(data["scalars"], agg_group_by, filters)
    except preprocessing.PreprocessingError:
        return graphs.get_empty_fig(), show_errors_and_warnings()
    try:
        fig = graphs.get_scalar_plot(preprocessed_data, graph_options)
    except graphs.PlottingError:
        return graphs.get_empty_fig(), show_errors_and_warnings()
    return fig, show_errors_and_warnings()


@app.callback(
    [
        Output(component_id='graph_timeseries', component_property='figure'),
        Output(component_id='graph_timeseries_error', component_property='children'),
    ],
    [
        Input(component_id="dd_scenario", component_property="value"),
        Input(component_id="aggregation_group_by", component_property="value"),
        Input(component_id="graph_timeseries_options_switch", component_property="value"),
    ] +
    [Input(component_id=f"filter_{filter_}", component_property='value') for filter_ in TS_FILTERS] +
    [
        Input(component_id=f"graph_timeseries_option_{option}", component_property='value')
        for option in GRAPHS_DEFAULT_OPTIONS["timeseries"]
    ]
)
def timeseries_graph(scenarios, agg_group_by, use_custom_graph_options, *filter_args):
    if scenarios is None:
        raise PreventUpdate
    data = get_multiple_scenario_data(*scenarios)
    filters, graph_options = preprocessing.extract_filters_and_options(
        "timeseries", filter_args, use_custom_graph_options
    )
    try:
        preprocessed_data = preprocessing.prepare_timeseries(data["timeseries"], agg_group_by, filters)
    except preprocessing.PreprocessingError:
        return graphs.get_empty_fig(), show_errors_and_warnings()
    try:
        fig = graphs.get_timeseries_plot(preprocessed_data, graph_options)
    except graphs.PlottingError:
        return graphs.get_empty_fig(), show_errors_and_warnings()
    return fig, show_errors_and_warnings()


def show_errors_and_warnings():
    errors = get_flashed_messages(category_filter=["error"])
    warnings = get_flashed_messages(category_filter=["warning"])
    infos = get_flashed_messages(category_filter=["info"])
    return get_error_and_warnings_div(errors, warnings, infos)

if __name__ == "__main__":
    app.run_server(debug=DEBUG)
