import os
import time
import json
import requests
from kafka import KafkaProducer

KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
WEATHER_API_KEY = os.environ["WEATHER_API_KEY"]
TOPIC = os.environ.get("TOPIC", "weather-raw")

API_URL = f"https://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q=Yerevan"

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

print("Producer started, polling every 60 seconds...")

while True:
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()

        producer.send(TOPIC, value=data)
        producer.flush()
        print(f"Sent weather data for {data['location']['name']}")

    except Exception as e:
        print(f"Error: {e}")

    time.sleep(60)