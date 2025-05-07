# IoT Device Code (ESP8266 + DHT11)

This folder contains Arduino code for three ESP8266-based devices used to monitor temperature and humidity in:
- Bedroom
- Office
- Outdoor

Each script connects to Wi-Fi, reads from a DHT11 sensor, and publishes readings via MQTT to specific topics:
- `esp8266/<location>/temperature`
- `esp8266/<location>/humidity`

The data is consumed by Telegraf and stored in InfluxDB.
