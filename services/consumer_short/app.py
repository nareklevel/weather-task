import os
import json
import psycopg2
from kafka import KafkaConsumer

KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
TOPIC = os.environ.get("TOPIC", "weather-raw")
GROUP_ID = os.environ.get("GROUP_ID", "short-writer")
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

print("Consumer short started, waiting for messages...")

for msg in consumer:
    try:
        data = msg.value
        city = data["location"]["name"]
        time_ = data["current"]["last_updated"]
        temp_c = data["current"]["temp_c"]
        temp_f = data["current"]["temp_f"]

        cursor.execute(
            "INSERT INTO weather_short (city, time, temperature_c, temperature_f) VALUES (%s, %s, %s, %s)",
            (city, time_, temp_c, temp_f)
        )
        print(f"Inserted into weather_short: {city} {time_}")
    except Exception as e:
        print(f"Error: {e}")