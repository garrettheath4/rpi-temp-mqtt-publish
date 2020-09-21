#!/usr/bin/env python3

"""
Source: https://github.com/adafruit/Adafruit_CircuitPython_PCT2075

Note: This adafruit_pct2075 library might not calculate the temperature
correctly since the PCT2075 seems to have an accuracy of less than 1 degree
Celsius whereas the TC74 only returns whole (integer) degrees Celsius.
"""

import logging
import os
from configparser import ConfigParser
import time
from datetime import datetime
from typing import Union

import board                                     # type: ignore
import digitalio                                 # type: ignore
import adafruit_tc74                             # type: ignore
# noinspection PyPep8Naming
import adafruit_mcp3xxx.mcp3008 as MCP           # type: ignore
from adafruit_mcp3xxx.analog_in import AnalogIn  # type: ignore
import paho.mqtt.client as mqtt                  # type: ignore

CONFIG_FILE_NAME = "config.ini"
DEFAULT_MQTT_TOPIC = "temperatureF"

MQTT_CONFIG_SECTION = "MQTT"
HOSTNAME_PROP_KEY = "Hostname"
TOPIC_PROP_KEY = "Topic"
TEMP_CONFIG_SECTION = "Temperature"
COMPONENT_PROP_KEY = "Component"

MIN_VALID_TEMP_C = -40
MAX_VALID_TEMP_C = 125


class _AbstractTempSensor:
    def __init__(self, sensor, temp_offset_c: float = 0):
        self.sensor = sensor
        self.temp_offset_c = temp_offset_c

    def read_raw_sensor_temp_c(self) -> float:
        return self.sensor.temperature

    def get_temperature_in_c(self) -> float:
        temp = self.read_raw_sensor_temp_c() + self.temp_offset_c
        assert MIN_VALID_TEMP_C <= temp <= MAX_VALID_TEMP_C, \
            "Temperature reading should be between {} C and {} C but was " \
            "instead {} C".format(MIN_VALID_TEMP_C, MAX_VALID_TEMP_C, temp)
        return temp


class DigitalTC74(_AbstractTempSensor):
    """
    Measures the temperature of a TC74 digital sensor component using
    the I2C data protocol.
    """
    TC74_I2C_ADDRESS = 0x48

    def __init__(self, i2c_address: int = TC74_I2C_ADDRESS,
                 temp_offset_c: float = -5):
        i2c = board.I2C()
        sensor = adafruit_tc74.TC74(i2c, address=i2c_address)
        super().__init__(sensor, temp_offset_c=temp_offset_c)
        if sensor.shutdown:
            sensor.shutdown = False
            if sensor.shutdown:
                logging.warning("Unable to set TC74 shutdown bit to False")
            else:
                logging.info("Successfully set TC74 shutdown bit to False")
        else:
            logging.info("TC74 sensor is in normal (non-shutdown) mode")


class AnalogTMP36(_AbstractTempSensor):
    """
    Measures the temperature of a TMP36 analog sensor component using an
    MCP3008 chip to convert the analog signal to a digital one. The
    analog sensor is connected to the channel 0 pin and the digital
    measurement is fetched from the MCP3008 using the SPI data protocol.
    The chip select pin is connected to GPIO 22.
    """

    def __init__(self):
        spi = board.SPI()
        chip_select = digitalio.DigitalInOut(board.D22)
        mcp = MCP.MCP3008(spi, chip_select)
        channel_0 = AnalogIn(mcp, MCP.P0)
        super().__init__(channel_0)

    def read_raw_sensor_temp_c(self) -> float:
        voltage = self.sensor.voltage
        logging.debug("Sensor value=%d voltage=%f", self.sensor.value, voltage)
        temp_c = (voltage * 1000 - 500) / 10
        return temp_c


def celsius_to_fahrenheit(celsius: float) -> float:
    return (celsius * 9 / 5) + 32


def check_and_publish_forever(sensor: _AbstractTempSensor,
                              mqtt_hostname: str,
                              mqtt_topic: str = DEFAULT_MQTT_TOPIC):
    mqtt_client = mqtt.Client()
    logging.info("Connecting to MQTT server at %s", mqtt_hostname)
    try:
        mqtt_client.connect(mqtt_hostname)
    except:  # catch *all* exceptions
        logging.exception("MQTT client connection exception caught")
        return False
    while True:
        temp_c = sensor.get_temperature_in_c()
        temp_f = celsius_to_fahrenheit(temp_c)
        logging.info("[%s]: %s: %f ºF (%f ºC)",
                     datetime.now(), mqtt_topic, temp_f, temp_c)
        try:
            info = mqtt_client.publish(mqtt_topic, round(temp_f, 2))
        except:  # catch *all* exceptions
            logging.exception("MQTT client publish exception caught")
            return False
        if info.rc != 0:
            logging.warning("Publish returned a non-zero return value %d",
                            info.rc)
            logging.debug(info)
            # a forever loop outside of this function can reconnect
            try:
                mqtt_client.disconnect()
            except:  # catch *all* exceptions
                logging.exception("MQTT client disconnect exception caught. "
                                  "Ignoring.")
            time.sleep(10.0)   # cooldown
            return
        time.sleep(60.0)


def get_config_prop(config: ConfigParser, section: str, key: str) \
        -> Union[str, bool]:
    if section not in config:
        return False
    if key not in config[section]:
        return False
    return config[section][key]


def main():
    hostname = ""
    mqtt_topic = DEFAULT_MQTT_TOPIC
    component = "TMP36"
    if os.path.isfile(CONFIG_FILE_NAME):
        config = ConfigParser()
        config.read(CONFIG_FILE_NAME)

        hostname_config_val = \
            get_config_prop(config, MQTT_CONFIG_SECTION, HOSTNAME_PROP_KEY)
        if hostname_config_val:
            hostname = hostname_config_val
        else:
            logging.error("No hostname found in the %s configuration file",
                          CONFIG_FILE_NAME)
            logging.error('Please set it by adding a "%s = hostname.com" '
                          'configuration value to the [%s] section of the '
                          'configuration file %s', HOSTNAME_PROP_KEY,
                          MQTT_CONFIG_SECTION, CONFIG_FILE_NAME)
            exit(1)

        topic_config_val = \
            get_config_prop(config, MQTT_CONFIG_SECTION, TOPIC_PROP_KEY)
        if topic_config_val:
            mqtt_topic = topic_config_val
        else:
            logging.warning("%s key not found in the %s configuration file",
                            TOPIC_PROP_KEY, CONFIG_FILE_NAME)
            logging.info("Using default MQTT topic: %s", mqtt_topic)

        component_config_val = \
            get_config_prop(config, TEMP_CONFIG_SECTION, COMPONENT_PROP_KEY)
        if component_config_val:
            if component_config_val.upper() == "TC74":
                component = "TC74"
        else:
            logging.warning("%s key not found in the %s configuration file",
                            COMPONENT_PROP_KEY, CONFIG_FILE_NAME)
            logging.info("Will try using default component: %s", component)
    else:
        logging.warning("No configuration file found at %s (current "
                        "directory: %s)", CONFIG_FILE_NAME, os.getcwd())

    if component.upper() == "TC74":
        sensor = DigitalTC74()
    else:
        sensor = AnalogTMP36()
    check_and_publish_forever(sensor, hostname, mqtt_topic)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    # If check_and_publish_forever function exits, go ahead and start over
    # from here to re-load the configuration and reinstantiate the objects
    while True:
        retval = main()
        if retval == False:
            logging.warning("Main loop encountered an error and returned False")
        logging.info("Sleeping for 60 seconds before restarting main loop")
        time.sleep(60)
