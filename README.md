TC74 Temperature Sensor
=======================

This is a Python library for communicating with the TC74 temperature sensor over
I2C on a Raspberry Pi in order to read the ambient (room) temperature. The
[TC74] aka TC74A0 aka TC74A0-5.0VAT is a temperature sensor from Adafruit that
uses the I2C data protocol to send and receive data from a controller device
(e.g. a Raspberry Pi).

Hardware
--------

### Board Pins (on Raspberry Pi)

I2C ports on Raspberry Pi are: GPIO (aka BCM) 2 for Data and GPIO 3 for Clock.

Run the `pinout` command to see the pins in the terminal on Rasperry Pi OS.
[pinout.xyz](https://pinout.xyz/pinout/i2c) is also a good reference.

| I2C Purpose | GPIO/BCM | Board Pin |
|-------------|----------|-----------|
| SDA (Data)  | GPIO 2   | Pin 3     |
| SCL (Clock) | GPIO 3   | Pin 5     |

### Firmware

In order to enable the I2C ports on a Raspberry Pi, you need to run `sudo
raspi-config` and go to _Interfacing Options > I2C > Enable_.  Then reboot with
`sudo reboot` and you should be able to run `sudo i2cdetect -y 1` without
getting an error. It should display a blank I2C address grid.

Source: [Adafruit Learn: GPIO Setup][LearnI2C]

### Sensor Pins

According to the [TC74 datasheet], the chip "package type" I received is the
TO-220 (breadboard form factor). It has 5 pins starting with 1 on the left to 5
on the right. They are:

* Pin 1 (left): NC (Not used)
* Pin 2: SDA (I2C Data)
* Pin 3 (middle): GND
* Pin 4: SCLK (I2C Clock)
* Pin 5 (right): VDD (power supply)

**Note:** You probably need to add pull-down resistors to the SDA (I2C Data) and
SCLK (I2C Clock) pins. Otherwise RF interference from the environment might
cause those floating pins to always be "high" (positive voltage).

Guides and Links
----------------

* [Adafruit PCT2075 Python library](https://github.com/adafruit/Adafruit_CircuitPython_PCT2075)
  on GitHub
* [Adafruit Learn MCP9809 I2C Temperature Sensor](https://learn.adafruit.com/circuitpython-basics-i2c-and-spi/i2c-devices)



<!-- Links -->
[TC74]: https://www.adafruit.com/product/4375
[LearnI2C]: https://learn.adafruit.com/adafruits-raspberry-pi-lesson-4-gpio-setup/configuring-i2c
[TC74 datasheet]: https://cdn-shop.adafruit.com/product-files/4375/4375_TC74A0-5.0VAT-Microchip-datasheet.pdf

<!-- vim: set textwidth=80: -->
