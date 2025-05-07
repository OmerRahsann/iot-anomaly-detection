import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

import duckdb
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Initialize DuckDB connection
con = duckdb.connect("edge_data.duckdb")
con.execute("""
    CREATE TABLE IF NOT EXISTS sensor_data (
        timestamp TIMESTAMP,
        location TEXT,
        type TEXT,
        value FLOAT
    )
""")

TEMP_MIN, TEMP_MAX = 10, 40
HUM_MIN, HUM_MAX = 20, 80


load_dotenv()

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")


last_alert_time = {}

def send_email_alert(subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)
        print("📧 Email sent!")

def detect_anomaly(sensor_type, value, location):
    if sensor_type == "temperature" and (value < TEMP_MIN or value > TEMP_MAX):
        return True, f"Temperature anomaly at {location}: {value}°C"
    if sensor_type == "humidity" and (value < HUM_MIN or value > HUM_MAX):
        return True, f"Humidity anomaly at {location}: {value}%"
    return False, ""

def should_send_alert(location, sensor_type):
    key = f"{location}-{sensor_type}"
    now = datetime.utcnow()
    if key not in last_alert_time or now - last_alert_time[key] > timedelta(hours=1):
        last_alert_time[key] = now
        return True
    return False

def on_connect(client, userdata, flags, rc):
    print("✅ Connected to MQTT Broker")
    client.subscribe("esp8266/+/temperature")
    client.subscribe("esp8266/+/humidity")

def on_message(client, userdata, msg):
    try:
        value = float(msg.payload.decode())
        timestamp = datetime.utcnow()
        topic_parts = msg.topic.split("/")
        location, sensor_type = topic_parts[1], topic_parts[2]

        con.execute("INSERT INTO sensor_data VALUES (?, ?, ?, ?)", (timestamp, location, sensor_type, value))
        print(f"📥 Logged: {timestamp} - {location} - {sensor_type} - {value}")

        is_anomaly, message = detect_anomaly(sensor_type, value, location)
        if is_anomaly and should_send_alert(location, sensor_type):
            print("⚠️  Anomaly detected!")
            send_email_alert("IoT Alert 🚨", message)
    except Exception as e:
        print("❌ Error:", e)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("127.0.0.1", 1883, 60)

print("📡 Listening for sensor data...")
client.loop_forever()
