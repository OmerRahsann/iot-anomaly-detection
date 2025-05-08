import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
from sklearn.ensemble import IsolationForest
from influxdb_client import InfluxDBClient
from email.message import EmailMessage
import smtplib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

now = datetime.now(timezone.utc)
start_time = (now - timedelta(days=1)).isoformat()
stop_time = now.isoformat()

flux_query = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: {start_time}, stop: {stop_time})
  |> filter(fn: (r) => r._measurement == "dht11_data")
  |> filter(fn: (r) => r.topic == "esp8266/office/temperature" or r.topic == "esp8266/office/humidity")
  |> pivot(rowKey:["_time"], columnKey: ["topic"], valueColumn: "_value")
'''

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()
df = query_api.query_data_frame(flux_query).reset_index(drop=True)

if df.empty:
    print("No Office data found.")
    exit()

df['time'] = pd.to_datetime(df['_time'])
temp_col = "esp8266/office/temperature"
hum_col = "esp8266/office/humidity"

if temp_col not in df.columns or hum_col not in df.columns:
    print("Temperature or Humidity column missing.")
    exit()

features = df[[temp_col, hum_col]].copy()
model = IsolationForest(contamination=0.05, random_state=42)
df['anomaly'] = model.fit_predict(features)

anomalies = df[df['anomaly'] == -1]
anomaly_times = anomalies['time'].sort_values().tolist()

def group_anomaly_periods(timestamps, threshold_minutes=5):
    if not timestamps:
        return []
    groups = []
    start = prev = timestamps[0]
    for current in timestamps[1:]:
        if (current - prev).seconds > threshold_minutes * 60:
            groups.append((start, prev))
            start = current
        prev = current
    groups.append((start, prev))
    return groups

anomaly_periods = group_anomaly_periods(anomaly_times)

plt.figure(figsize=(14, 6))
plt.plot(df['time'], df[temp_col], label="Temperature (°C)", color='blue')
plt.plot(df['time'], df[hum_col], label="Humidity (%)", color='green')
plt.scatter(anomalies['time'], anomalies[temp_col], color='red', s=12, label="Anomaly (Temp Only)")
plt.title("Daily Office Sensor Report – Temperature & Humidity")
plt.xlabel("Time")
plt.ylabel("Sensor Value")
plt.legend()
plt.tight_layout()
plt.savefig("office_daily_report.png")
plt.close()

# Format anomaly report for email
if anomaly_periods:
    body_lines = ["📊 Daily Office Sensor Report (last 24h):", "", "⚠️ Anomaly Periods Detected:"]
    for start, end in anomaly_periods:
        body_lines.append(f"- {start.strftime('%Y-%m-%d %H:%M')} – {end.strftime('%H:%M')}")
else:
    body_lines = [
        "📊 Daily Office Sensor Report (last 24h):",
        "",
        "✅ No anomalies detected."
    ]
email_body = "\n".join(body_lines)

msg = EmailMessage()
msg.set_content(email_body)
msg["Subject"] = "📈 Daily IoT Report – Office Sensors"
msg["From"] = EMAIL_SENDER
msg["To"] = EMAIL_RECEIVER

with open("office_daily_report.png", "rb") as f:
    msg.add_attachment(f.read(), maintype="image", subtype="png", filename="office_daily_report.png")

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)
        print("✅ Daily report with anomaly periods sent.")
except Exception as e:
    print("❌ Email failed:", e)
