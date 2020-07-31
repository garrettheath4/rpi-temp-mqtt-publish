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
import adafruit_tc74

TC74_TO_220_I2C_ADDRESS=0x48

i2c = busio.I2C(board.SCL, board.SDA)

tc74 = adafruit_tc74.TC74(i2c, address=TC74_TO_220_I2C_ADDRESS)

def main():
    if tc74.shutdown:
        tc74.shutdown = False
        if tc74.shutdown != False:
            print("Unable to set shutdown bit to False")
        else:
            print("Successfully set shutdown bit to False")
    else:
        print("Sensor is in normal (non-shutdown) mode")
    while True:
        print(f"Data ready:  {tc74.data_ready}")
        print(f"  raw temp:  {tc74._temperature:08b}")
        print(f"Temperature: {tc74.temperature:.1f}")
        print("====")
        time.sleep(2.0)


if __name__ == '__main__':
    main()
