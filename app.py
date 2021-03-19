import os
import pathlib

import urllib3
import jmespath

import dash
from dash.dependencies import Input, Output
from flask_caching import Cache
from layout import get_layout
from settings import FILTERS
import scenario

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

# Cache

CACHE_CONFIG = {
    # try 'filesystem' if you don't want to setup redis
    "CACHE_TYPE": "filesystem",
    "CACHE_REDIS_URL": os.environ.get("REDIS_URL"),
    "CACHE_DIR": "cache-directory",
}
cache = Cache()
cache.init_app(server, config=CACHE_CONFIG)


@cache.memoize()
def get_scenario_data(scenario_id):
    return scenario.get_scenario_data(scenario_id)


@cache.memoize()
def get_multiple_scenario_data(*scenario_ids):
    scenarios = [
        scenario.get_scenario_data(scenario_id) for scenario_id in scenario_ids
    ]
    return scenario.merge_scenario_data(scenarios)


@app.callback(
    [Output(component_id=f"filter_{filter_}", component_property="options") for filter_ in FILTERS],
    [Input(component_id="dd_scenario", component_property="value")],
)
def load_scenario(scenarios):
    if scenarios is None:
        return [[] for _ in FILTERS]
    scenarios = scenarios if isinstance(scenarios, list) else [scenarios]
    data = get_multiple_scenario_data(*scenarios)
    filters = {}
    for filter_, filter_format in FILTERS.items():
        jmespath_str = f"[oed_scalars, oed_timeseries][].{filter_}"
        if filter_format["type"] == "list":
            jmespath_str += "[]"
        filters[filter_] = set(jmespath.search(jmespath_str, data))
    output = (
        [{"label": filter_option, "value": filter_option} for filter_option in filter_options]
        for _, filter_options in filters.items()
    )
    return list(output)


if __name__ == "__main__":
    app.run_server(debug=True)
