#!/usr/bin/env python3

"""
Source: https://github.com/adafruit/Adafruit_CircuitPython_PCT2075

Note: This adafruit_pct2075 library might not calculate the temperature
correctly since the PCT2075 seems to have an accuracy of less than 1 degree
celcius whereas the TC74 only returns whole (integer) degrees celcius.
"""

import time
from datetime import datetime

import board
import busio
import adafruit_tc74
import paho.mqtt.client as mqtt

TC74_TO_220_I2C_ADDRESS=0x48
MQTT_TOPIC_TEMPERATURE = "perupino/garrett/temperatureF"

def main():
    temp_offset_c = -5

    i2c = busio.I2C(board.SCL, board.SDA)
    tc74 = adafruit_tc74.TC74(i2c, address=TC74_TO_220_I2C_ADDRESS)

    client = mqtt.Client()
    client.connect("mqtt.garrettheath4.com", 1883, 60)

    if tc74.shutdown:
        tc74.shutdown = False
        if tc74.shutdown != False:
            print("Unable to set shutdown bit to False")
        else:
            print("Successfully set shutdown bit to False")
    else:
        print("Sensor is in normal (non-shutdown) mode")
    while True:
        temp_c = tc74.temperature + temp_offset_c
        temp_f = (temp_c * 9 / 5) + 32
        print(f"[{datetime.now()}]: {MQTT_TOPIC_TEMPERATURE}: {temp_f} ºF ({temp_c} ºC)")
        client.publish(MQTT_TOPIC_TEMPERATURE, temp_f)
        time.sleep(60.0)

if __name__ == "__main__":
    main()
