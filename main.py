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
            response = response.json()
        #print(response.json())


        for i in range(len(response["hourly"]["time"])):
            insert_hourly_weather(city_id, response["hourly"]["time"][i], response["hourly"]["temperature_2m"][i], response["hourly"]["wind_speed_10m"][i])

        #print(response["hourly"]["time"][0],response["hourly"]["temperature_2m"][0], response["hourly"]["wind_speed_10m"][0])
        
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

def insert_hourly_weather(city_id: int, timestamp_utc: str, temperature_c: float, wind_speed_ms: float) -> None:
    """Insert hourly weather data into the database."""
    conn = sqlite3.connect(DATABASE_PATH)

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO hourly_weather
                (city_id, timestamp_utc, temperature_c, wind_speed_ms)
            VALUES (?, ?, ?, ?)
            """,
            (city_id, timestamp_utc, temperature_c, wind_speed_ms),
        )
        conn.commit()
    except sqlite3.Error:
        print(f"Failed to save hourly weather for city {city_id}.")
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    main()
