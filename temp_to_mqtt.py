#!/usr/bin/env python3

"""
Source: https://github.com/adafruit/Adafruit_CircuitPython_PCT2075

Note: This adafruit_pct2075 library might not calculate the temperature
correctly since the PCT2075 seems to have an accuracy of less than 1 degree
Celsius whereas the TC74 only returns whole (integer) degrees Celsius.
"""

import logging
from pathlib import Path
from configparser import ConfigParser
import time
from datetime import datetime
from typing import Union

import board
import digitalio
import adafruit_tc74
# noinspection PyPep8Naming
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import paho.mqtt.client as mqtt

CONFIG_FILE_NAME = "config.ini"
DEFAULT_MQTT_TOPIC = "temperatureF"
MQTT_CONFIG_SECTION = "MQTT"
HOSTNAME_PROP_KEY = "Hostname"
TOPIC_PROP_KEY = "Topic"
TEMP_CONFIG_SECTION = "Temperature"
COMPONENT_PROP_KEY = "Component"


class _AbstractTempSensor:
    def __init__(self, sensor, temp_offset_c: float = 0):
        self.sensor = sensor
        self.temp_offset_c = temp_offset_c

    def get_temperature_in_c(self) -> float:
        return self.sensor.temperature + self.temp_offset_c

    def get_temperature_in_f(self) -> float:
        return (self.get_temperature_in_c() * 9 / 5) + 32


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

    def get_temperature_in_c(self) -> float:
        return self.sensor.value


def check_and_publish_forever(sensor: _AbstractTempSensor,
                              mqtt_hostname: str,
                              mqtt_topic: str = DEFAULT_MQTT_TOPIC):
    mqtt_client = mqtt.Client()
    mqtt_client.connect(mqtt_hostname)
    while True:
        temp_c = sensor.get_temperature_in_c()
        temp_f = sensor.get_temperature_in_f()
        logging.info("[{}]: {}: {} ºF ({} ºC)".format(
            datetime.now(), mqtt_topic, temp_f, temp_c))
        info = mqtt_client.publish(mqtt_topic, temp_f)
        if info.rc != 0:
            logging.warning("Publish returned a non-zero return "
                            "value {}".format(info.rc))
            logging.debug(info)
            # a forever loop outside of this function can reconnect
            mqtt_client.disconnect()
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
    config_path = Path(CONFIG_FILE_NAME)
    hostname = ""
    mqtt_topic = DEFAULT_MQTT_TOPIC
    component = "TMP36"
    if config_path.is_file():
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
        main()
