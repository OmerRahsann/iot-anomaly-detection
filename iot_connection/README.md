# IoT Device Code (ESP8266 + DHT11)

This folder contains Arduino code for three ESP8266-based devices used to monitor temperature and humidity in:
- Bedroom
- Office
- Outdoor

Each script:
- Connects to Wi-Fi
- Reads temperature and humidity from a DHT11 sensor
- Publishes data via MQTT to the following topics:
  - `esp8266/<location>/temperature`
  - `esp8266/<location>/humidity`

## MQTT Setup
The devices connect to a local MQTT broker running on `10.0.0.111:1883`

## Telegraf Integration
Telegraf listens for MQTT messages on topic `esp8266/#` using the `mqtt_consumer` input plugin. It is configured to:
- Subscribe to MQTT topics
- Format incoming data as float values
- Forward the metrics to InfluxDB for storage and visualization


