import os
import json
import psycopg2
from kafka import KafkaConsumer

KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
TOPIC = os.environ.get("TOPIC", "weather-raw")
GROUP_ID = os.environ.get("GROUP_ID", "long-writer")
DB_HOST = os.environ["DB_HOST"]
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]

conn = psycopg2.connect(
    host=DB_HOST, port=DB_PORT,
    dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
)
conn.autocommit = True
cursor = conn.cursor()

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id=GROUP_ID,
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    auto_offset_reset="earliest"
)

print("Consumer long started, waiting for messages...")

for msg in consumer:
    try:
        d = msg.value
        loc = d["location"]
        cur = d["current"]

        cursor.execute(
            """
            INSERT INTO weather_long (
                city, region, country, lat, lon, tz_id, localtime,
                last_updated, temp_c, temp_f, is_day, condition_text, condition_code,
                wind_mph, wind_kph, wind_degree, wind_dir,
                pressure_mb, pressure_in, precip_mm, precip_in,
                humidity, cloud, feelslike_c, feelslike_f,
                windchill_c, windchill_f, heatindex_c, heatindex_f,
                dewpoint_c, dewpoint_f, vis_km, vis_miles,
                uv, gust_mph, gust_kph, short_rad, diff_rad, dni, gti
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s
            )
            """,
            (
                loc["name"], loc["region"], loc["country"],
                loc["lat"], loc["lon"], loc["tz_id"], loc["localtime"],
                cur["last_updated"], cur["temp_c"], cur["temp_f"],
                cur["is_day"], cur["condition"]["text"], cur["condition"]["code"],
                cur["wind_mph"], cur["wind_kph"], cur["wind_degree"], cur["wind_dir"],
                cur["pressure_mb"], cur["pressure_in"],
                cur["precip_mm"], cur["precip_in"],
                cur["humidity"], cur["cloud"],
                cur["feelslike_c"], cur["feelslike_f"],
                cur["windchill_c"], cur["windchill_f"],
                cur["heatindex_c"], cur["heatindex_f"],
                cur["dewpoint_c"], cur["dewpoint_f"],
                cur["vis_km"], cur["vis_miles"],
                cur["uv"], cur["gust_mph"], cur["gust_kph"],
                cur.get("short_rad", 0), cur.get("diff_rad", 0),
                cur.get("dni", 0), cur.get("gti", 0)
            )
        )
        print(f"Inserted into weather_long: {loc['name']} {cur['last_updated']}")
    except Exception as e:
        print(f"Error: {e}")
