"""Optional starting point. See README.md for the task; reorganise freely."""

from pathlib import Path
import httpx
import sqlite3
import json

API_URL = "https://api.open-meteo.com/v1/forecast"

CITIES = {
    "London": (51.5072, -0.1276),
    "Paris": (48.8566, 2.3522),
    "Madrid": (40.4168, -3.7038),
}

PROJECT_DIR = Path(__file__).resolve().parent
SAMPLE_PATH = PROJECT_DIR / "sample-weather.json"
DATABASE_PATH = PROJECT_DIR / "weather.sqlite3"


def main() -> None:
    """Implement the pipeline and demonstrate the SQL queries."""
    # Choose your own functions, classes, modules, and input-selection approach.
    create_database()
    for city in CITIES:
        city_id = insert_city(city, CITIES[city][0], CITIES[city][1])

        flag = API_URL == api_route(disable=True)
        if not flag:
            print(f"API route is disabled. Using local file: {SAMPLE_PATH}")
            with open(SAMPLE_PATH, "r") as f:
                sample_data = json.load(f)
            response = sample_data[city]
        else:
            response = httpx.get(API_URL + f"?latitude={CITIES[city][0]}&longitude={CITIES[city][1]}"+f"&hourly=temperature_2m,wind_speed_10m&temperature_unit=celsius&wind_speed_unit=ms&timezone=GMT&forecast_hours=48")
            if response.status_code != 200:
                print(f"Failed to fetch data for {city}. Status code: {response.status_code}")
                continue
            response = response.json()


        for i in range(len(response["hourly"]["time"])):
            rolling_mean_c = None
            skip = False
            if i >= 2:
                window = response["hourly"]["temperature_2m"][i - 2:i + 1]

                for temp in window:
                    if temp is None:
                        skip = True
                        break
                if not skip:
                    rolling_mean_c = sum(window) / 3

            insert_hourly_weather(city_id, response["hourly"]["time"][i], response["hourly"]["temperature_2m"][i], response["hourly"]["wind_speed_10m"][i],rolling_mean_c)

        timestamps = response["hourly"]["time"]
        avg_temps = avg_temp_per_city(
            city_id, min(timestamps), max(timestamps)
        )
        for city_name, avg_temp in avg_temps:
            print(f"\nAverage temperature for {city_name}: {avg_temp:.2f} °C")

        windiest_hours = windiest_hours_per_city(
            city_id, min(timestamps), max(timestamps)
        )
        print(f"Windiest hours for {city}:")
        for city_name, timestamp_utc, wind_speed in windiest_hours:
            print(f"{city_name}: {timestamp_utc} with wind speed {wind_speed:.2f} m/s")

        
def api_route(disable: bool = False) -> str:
    """Return the API route, or a local file path if disabled."""
    if disable:
        return SAMPLE_PATH
    return API_URL

def create_database():
    """Create the SQLite database and tables."""
    sql_statements = [ 
        """CREATE TABLE IF NOT EXISTS cities (
                city_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL
            );""",

        """ CREATE TABLE IF NOT EXISTS hourly_weather (
                city_id INTEGER NOT NULL,
                timestamp_utc TEXT NOT NULL,
                temperature_c REAL,
                wind_speed_ms REAL,
                rolling_mean_c REAL,
                PRIMARY KEY (city_id, timestamp_utc),
                FOREIGN KEY (city_id) REFERENCES cities(city_id)
            );"""
    ]

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        for statement in sql_statements:
            cursor.execute(statement)
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as e:
        print(e)

def insert_city(name: str, latitude: float, longitude: float) -> int:
    """Return the city's ID, creating the city if needed."""
    conn = sqlite3.connect(DATABASE_PATH)

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT city_id FROM cities WHERE name = ?",
            (name,),
        )
        city = cursor.fetchone()

        if city is not None:
            return city[0]

        cursor.execute(
            "INSERT INTO cities (name, latitude, longitude) VALUES (?, ?, ?)",
            (name, latitude, longitude),
        )
        conn.commit()

        cursor.execute(
            "SELECT city_id FROM cities WHERE name = ?",
            (name,),
        )
        city = cursor.fetchone()

        return city[0]
    except sqlite3.Error:
        print(f"Failed to save city {name}.")
        raise

    finally:
        conn.close()

def insert_hourly_weather(city_id: int, timestamp_utc: str, temperature_c: float, wind_speed_ms: float, rolling_mean_c: float) -> None:
    """Insert hourly weather data into the database."""
    conn = sqlite3.connect(DATABASE_PATH)

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO hourly_weather
                (city_id, timestamp_utc, temperature_c, wind_speed_ms, rolling_mean_c)
            VALUES (?, ?, ?, ?, ?)
            """,
            (city_id, timestamp_utc, temperature_c, wind_speed_ms, rolling_mean_c),
        )
        conn.commit()
    except sqlite3.Error:
        print(f"Failed to save hourly weather for city {city_id}.")
        raise

    finally:
        conn.close()

def avg_temp_per_city(city_id: int, start_utc: str, end_utc: str) -> list[tuple[str, float]]:
    """Return a city's average temperature over its input window."""
    conn = sqlite3.connect(DATABASE_PATH)

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.name, AVG(hw.temperature_c) AS avg_temp
            FROM cities c
            JOIN hourly_weather hw ON c.city_id = hw.city_id
            WHERE hw.city_id = ?
              AND hw.timestamp_utc BETWEEN ? AND ?
            GROUP BY c.name
            """,
            (city_id, start_utc, end_utc),
        )
        results = cursor.fetchall()
        return results
    except sqlite3.Error:
        print("Failed to retrieve average temperature per city.")
        raise

    finally:
        conn.close()

def windiest_hours_per_city(city_id: int, start_utc: str, end_utc: str) -> list[tuple[str, str, float]]:
    """Return up to five windiest hours for a city in its input window."""
    conn = sqlite3.connect(DATABASE_PATH)

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.name, hw.timestamp_utc, hw.wind_speed_ms
            FROM cities c
            JOIN hourly_weather hw ON c.city_id = hw.city_id
            WHERE hw.city_id = ?
              AND hw.timestamp_utc BETWEEN ? AND ?
              AND hw.wind_speed_ms IS NOT NULL
            ORDER BY hw.wind_speed_ms DESC, hw.timestamp_utc ASC
            LIMIT 5
            """,
            (city_id, start_utc, end_utc),
        )
        results = cursor.fetchall()
        return results
    except sqlite3.Error:
        print("Failed to retrieve windiest hours per city.")
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    main()
