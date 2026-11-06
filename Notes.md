## Setup and run

- Python version used: 3.13.0
- Dependencies: httpx 0.28.1, polars 2.0.0 (not used tho)
- Enviroment tool: uv

With uv installed, run this from the project directory:

    uv run --locked python main.py

This installs the locked dependencies and runs the pipeline.
Sample input is enabled by default using `disable=True` in main.py.
Change this to `disable=False` to use the live API.

## Proofs

SELECT * FROM cities;
╭─────────┬────────┬──────────┬───────────╮
│ city_id │  name  │ latitude │ longitude │
╞═════════╪════════╪══════════╪═══════════╡
│       1 │ London │  51.5072 │   -0.1276 │
│       2 │ Paris  │  48.8566 │    2.3522 │
│       3 │ Madrid │  40.4168 │   -3.7038 │
╰─────────┴────────┴──────────┴───────────╯


- Proof of the rolling mean beaing calculated and stored in the database
╭─────────┬──────────────────┬───────────────┬───────────────┬───────────────────╮
│ city_id │  timestamp_utc   │ temperature_c │ wind_speed_ms │  rolling_mean_c   │
╞═════════╪══════════════════╪═══════════════╪═══════════════╪═══════════════════╡
│       1 │ 2026-01-15T00:00 │           8.0 │           3.1 │ NULL              │
│       1 │ 2026-01-15T01:00 │           7.0 │          5.55 │ NULL              │
│       1 │ 2026-01-15T02:00 │           6.0 │          3.45 │               7.0 │
│       1 │ 2026-01-15T03:00 │           6.0 │           5.9 │ 6.333333333333333 │
│       1 │ 2026-01-15T04:00 │           7.0 │           3.8 │ 6.333333333333333 │
│       1 │ 2026-01-15T05:00 │           8.0 │          6.25 │               7.0 │
│       1 │ 2026-01-15T06:00 │           9.0 │          4.15 │               8.0 │
│       1 │ 2026-01-15T07:00 │          10.0 │           6.6 │               9.0 │
│       1 │ 2026-01-15T08:00 │          11.0 │           4.5 │              10.0 │
│       1 │ 2026-01-15T09:00 │          12.0 │          6.95 │              11.0 │
╰─────────┴──────────────────┴───────────────┴───────────────┴───────────────────╯

London’s first three temperatures are 8, 7 and 6°C.
(8 + 7 + 6) / 3 = 7°C, matching the stored rolling mean at 2026-01-15T02:00. The first two rolling means are NULL because three temperatures aren’t available yet.


- Proof loading the same sample twice doesn’t add duplicates

Running the databse the first time:
SELECT COUNT(*) AS city_count FROM cities;
╭────────────╮
│ city_count │
╞════════════╡
│          3 │
╰────────────╯
SELECT COUNT(*) AS weather_count FROM hourly_weather;
╭───────────────╮
│ weather_count │
╞═══════════════╡
│           144 │
╰───────────────╯

After I run the script the 2nd time:

SELECT COUNT(*) AS city_count FROM cities;
╭────────────╮
│ city_count │
╞════════════╡
│          3 │
╰────────────╯
SELECT COUNT(*) AS weather_count FROM hourly_weather;
╭───────────────╮
│ weather_count │
╞═══════════════╡
│           144 │
╰───────────────╯

The use of INSERT OR REPLACE insures we dont keep making new rows for the same hours it just repalces the data if the data updates.

-Proof that changing a sample temperature updates the existing data.

SELECT timestamp_utc, temperature_c, rolling_mean_c
FROM hourly_weather
WHERE city_id = 1
    AND timestamp_utc BETWEEN '2026-01-15T02:00' AND '2026-01-15T04:00'
ORDER BY timestamp_utc;

╭──────────────────┬───────────────┬───────────────────╮
│  timestamp_utc   │ temperature_c │  rolling_mean_c   │
╞══════════════════╪═══════════════╪═══════════════════╡
│ 2026-01-15T02:00 │           6.0 │               7.0 │
│ 2026-01-15T03:00 │           6.0 │ 6.333333333333333 │
│ 2026-01-15T04:00 │           7.0 │ 6.333333333333333 │
╰──────────────────┴───────────────┴───────────────────╯

SELECT COUNT(*) AS city_count FROM cities;
╭────────────╮
│ city_count │
╞════════════╡
│          3 │
╰────────────╯
SELECT COUNT(*) AS weather_count FROM hourly_weather;
╭───────────────╮
│ weather_count │
╞═══════════════╡
│           288 │
╰───────────────╯

(Note the count is 288 due to the API window data and then the sample window data which is why theres two lots of 144)

Then changing London’s third temperature in the sample file from 6 to 9:


With api_route(disable=True), I ran uv run --locked python main.py, then repeated the SQL queries above.:

╭──────────────────┬───────────────┬───────────────────╮
│  timestamp_utc   │ temperature_c │  rolling_mean_c   │
╞══════════════════╪═══════════════╪═══════════════════╡
│ 2026-01-15T02:00 │           9.0 │               8.0 │
│ 2026-01-15T03:00 │           6.0 │ 7.333333333333333 │
│ 2026-01-15T04:00 │           7.0 │ 7.333333333333333 │
╰──────────────────┴───────────────┴───────────────────╯
╭────────────╮
│ city_count │
╞════════════╡
│          3 │
╰────────────╯
╭───────────────╮
│ weather_count │
╞═══════════════╡
│           288 │
╰───────────────╯

## Assumptions and limitations

- I assume the input contains consecutive UTC hours in chronological order,
  with matching timestamp, temperature and wind-speed arrays.
- Missing measurements remain NULL. A rolling mean is NULL unless all
  three required temperatures are present.
- Rolling means use only the current input, without earlier database rows.
- Rows outside the incoming forecast window are retained.
- A non-200 API response is reported and that city is skipped.

## Time spent

Approximately 4 hours.

## Assistance used

I used Chat GPT to list requirements in an easier format

