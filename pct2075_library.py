#!/usr/bin/env python3

"""
Source: https://github.com/adafruit/Adafruit_CircuitPython_PCT2075

Note: This adafruit_pct2075 library might not calculate the temperature
correctly since the PCT2075 seems to have an accuracy of less than 1 degree
celcius whereas the TC74 only returns whole (integer) degrees celcius.
"""

import time
import board
import busio
import adafruit_pct2075

TC74_TO_220_I2C_ADDRESS=0x48

i2c = busio.I2C(board.SCL, board.SDA)

pct = adafruit_pct2075.PCT2075(i2c, address=TC74_TO_220_I2C_ADDRESS)

while True:
    print(f"Temperature: {pct.temperature:.2f}")
    time.sleep(0.5)

