# Data Engineering Interview Task

Build a small Python pipeline that fetches hourly weather forecasts, transforms
them, and stores them in SQLite. Bring your code to the interview so we can run
it together and discuss your decisions.


## Time and scope

Aim for three hours and stop after four. An incomplete submission with clear
notes is welcome.

Use Python and SQLite. We typically use HTTPX for HTTP requests and Polars for
data transformations, so the starter includes those libraries. They are
suggestions, not requirements: requests, pandas, or other approaches are equally
welcome. Library and environment-tool choices are not assessed; use tools you
understand and can explain. Run locally; deployment, scheduling, dashboards, and
production resilience are outside scope.

The starter files are optional. Choose your own functions, classes, and file
layout. A single well-organised Python file is acceptable.


## Fetch the data

Fetch 48 hourly forecast values for each of these cities:

| City | Latitude | Longitude |
| --- | ---: | ---: |
| London | 51.5072 | -0.1276 |
| Paris | 48.8566 | 2.3522 |
| Madrid | 40.4168 | -3.7038 |

Use the [Open-Meteo forecast API](https://open-meteo.com/en/docs). Request
temperature in Celsius, wind speed in metres per second, and timestamps in UTC.

This example requests 48 hourly values beginning at the current hour. These are
forecasts, not observations.

```text
https://api.open-meteo.com/v1/forecast?latitude=51.5072&longitude=-0.1276&hourly=temperature_2m,wind_speed_10m&temperature_unit=celsius&wind_speed_unit=ms&timezone=GMT&forecast_hours=48
```

Use a request timeout. Stopping with a clear error on failure is sufficient.

`sample_weather.json` contains synthetic API-shaped responses keyed by city
name: 48 consecutive UTC hours per city from 2026-01-15 00:00. Use it for
repeatable checks and an offline demonstration. Switching input with a variable
is fine. If API access blocks you, continue with the sample and note the issue.


## Transform the data

Create a tidy tabular dataset with one row per city and forecast timestamp,
containing:

- City identity and name, plus latitude and longitude.
- A UTC timestamp.
- Temperature in Celsius and wind speed in metres per second.
- A three-hour rolling mean temperature for that city.

Calculate the rolling mean separately per city, in time order, using the current
and two preceding hours. Require all three temperatures; otherwise leave the
mean missing, including the first two rows per city. Use only the input window;
no earlier database rows are needed.

Keep missing measurements as missing, rather than replacing them with zero. The
sample includes one missing London temperature.


## Store the data

Design linked SQLite tables for cities and hourly weather values. Choose your
own keys, columns, and constraints. A separate time dimension is not required.

Include schema creation in code or SQL, and load using sqlite3 and parameterised
SQL.

Your database must retain at most one weather row per city and UTC timestamp:

- Loading the same input again must not add duplicate city or weather rows.
- Changed values for an existing city and timestamp must update the stored
  measurements and derived value.
- Retain rows outside the incoming window. Do not delete and rebuild the
  database on every run.

The most recently loaded input wins. Forecast version history and out-of-order
arrivals are outside scope.


## Query and demonstrate

Using SQL executed through sqlite3, show:

1. Average temperature per city over the input window used for the demonstration.
2. The five windiest hours per city over that same window, including timestamps
   and wind speeds. Choose a consistent tie-break rule.

Use the input timestamps to define the window, so queries also work with the
fixed sample. Display results in the terminal.

Include these checks, automated or documented as reproducible steps:

- Check a rolling mean against a value calculated by hand.
- Load the same sample twice and show unchanged row counts. A fresh sample load
  should contain three cities and 144 weather rows.
- Change one sample temperature, reload, and show the stored measurement and
  affected rolling means update without adding rows.


## What to bring

Bring the source code and a short `NOTES.md` containing:

- Your Python version, dependencies, and exact setup/run commands.
- How to select sample input and reproduce your checks.
- Assumptions, known limitations, and unfinished work.
- Approximate time spent.
- Any AI tools, external code, or substantial assistance used.

### AI assistance

We would prefer you to complete the exercise without generative AI assistance,
including AI code completion, so we can discuss your own approach. Documentation
and other online reference material are welcome.

If you do use AI, disclose the tools used and what they helped with in
`NOTES.md`. You must understand and be able to explain every line of code you
submit, check its correctness, and make changes yourself during the interview.
If you get stuck, an incomplete solution with clear notes is welcome; do not use
AI simply to finish within the time limit.

We assess correctness, readability, SQL, your checks, and your reasoning. Extra
features are not required for a strong submission.

At the interview, demonstrate the pipeline, explain your choices, discuss a
failure or missing-data case, and work through a small change with us.


## Starter files

- `pyproject.toml` defines the project, Python version, and dependencies.
- `uv.lock` records the resolved dependency versions. Include it if using uv.
- `.python-version` selects Python 3.13 for the default uv setup.
- `main.py` supplies locations, request parameters, and an empty entry point.
- `sample_weather.json` supplies the sample described above.

We've provided a uv project for convenience. You're welcome to use another
setup; include instructions to reproduce it. You may change the dependencies and
Python version.

### Default setup with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run
this from the project directory:

```bash
uv run --locked python main.py
```

This sets up the project environment and installs the locked dependencies. uv
can also download the selected Python version if needed. The first run requires
internet access for setup; the supplied sample can then be used for an offline
demonstration.

The starter deliberately raises `NotImplementedError` until you implement the
pipeline. This is expected, not a setup failure.

If you change dependencies, use `uv add` / `uv remove`, or edit `pyproject.toml`
and run `uv lock`. Include the updated `pyproject.toml` and `uv.lock` in your
submission. For example, to use pandas and requests instead:

```bash
uv remove polars httpx
uv add pandas requests
```

If using another environment tool, install your chosen dependencies and document
how to run your solution. Do not submit your virtual environment or generated
database.
