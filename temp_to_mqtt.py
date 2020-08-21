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
import busio
import adafruit_tc74
import paho.mqtt.client as mqtt

CONFIG_FILE_NAME = "config.ini"
TC74_I2C_ADDRESS = 0x48
DEFAULT_MQTT_TOPIC = "perupino/garrett/temperatureF"
MQTT_CONFIG_SECTION = "MQTT"
HOSTNAME_PROP_KEY = "Hostname"
PORT_PROP_KEY = "Port"
TOPIC_PROP_KEY = "MqttTopic"
TEMP_CONFIG_SECTION = "Temperature"
COMPONENT_PROP_KEY = "Component"


class AbstractSensorWrapper:
    def __init__(self, sensor, temp_offset_c: float = 0):
        self.sensor = sensor
        self.temp_offset_c = temp_offset_c

    def get_temperature_in_c(self) -> float:
        return self.sensor.temperature + self.temp_offset_c

    def get_temperature_in_f(self) -> float:
        return (self.get_temperature_in_c() * 9 / 5) + 32


class TC74(AbstractSensorWrapper):
    def __init__(self, i2c_address: int = TC74_I2C_ADDRESS,
                 temp_offset_c: float = -5):
        i2c = busio.I2C(board.SCL, board.SDA)
        sensor = adafruit_tc74.TC74(i2c, address=TC74_I2C_ADDRESS)
        super().__init__(sensor, temp_offset_c=temp_offset_c)
        if sensor.shutdown:
            sensor.shutdown = False
            if sensor.shutdown:
                logging.warning("Unable to set TC74 shutdown bit to False")
            else:
                logging.info("Successfully set TC74 shutdown bit to False")
        else:
            logging.info("TC74 sensor is in normal (non-shutdown) mode")


class TMP36(AbstractSensorWrapper):
    def __init__(self, sensor):
        # TODO
        super().__init__(sensor)


def check_and_publish(sensor: AbstractSensorWrapper, client: mqtt.Client):
    while True:
        temp_c = sensor.get_temperature_in_c()
        temp_f = sensor.get_temperature_in_f()
        logging.info(f"[{datetime.now()}]: {DEFAULT_MQTT_TOPIC}: "
                     f"{temp_f} ºF ({temp_c} ºC)")
        info: mqtt.MQTTMessageInfo = client.publish(DEFAULT_MQTT_TOPIC, temp_f)
        if info.rc != 0:
            logging.warning(f"Publish returned a non-zero return value"
                            f" {info.rc}")
            logging.debug(info)
            logging.info("Attempting to reconnect")
            client.disconnect()
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
    config_path: Path = Path(CONFIG_FILE_NAME)
    hostname: str = ""
    port: int = 1883
    mqtt_topic: str = DEFAULT_MQTT_TOPIC
    component: str = "TMP36"
    if config_path.is_file():
        config = ConfigParser()
        config.read(CONFIG_FILE_NAME)

        hostname_config_val = get_config_prop(config, MQTT_CONFIG_SECTION,
                                              HOSTNAME_PROP_KEY)
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

        port_config_val = get_config_prop(config, MQTT_CONFIG_SECTION,
                                          PORT_PROP_KEY)
        if port_config_val:
            port = port_config_val
        else:
            logging.warning("%s key not found in the %s configuration file",
                            HOSTNAME_PROP_KEY, CONFIG_FILE_NAME)
            logging.info("Using default port number: %d", port)

        topic_config_val = get_config_prop(config, MQTT_CONFIG_SECTION,
                                           TOPIC_PROP_KEY)
        if topic_config_val:
            mqtt_topic = topic_config_val
        else:
            logging.warning("%s key not found in the %s configuration file",
                            TOPIC_PROP_KEY, CONFIG_FILE_NAME)
            logging.info("Using default MQTT topic: %s", mqtt_topic)

        component_config_val = get_config_prop(config, TEMP_CONFIG_SECTION,
                                               COMPONENT_PROP_KEY)
        if component_config_val:
            if component_config_val.upper() == "TC74":
                component = "TC74"
        else:
            logging.warning("%s key not found in the %s configuration file",
                            COMPONENT_PROP_KEY, CONFIG_FILE_NAME)
            logging.info("Will try using default component: %s", component)

    if component.upper() == "TC74":
        sensor = TC74()
    else:
        #TODO
        sensor = TMP36()
    client = mqtt.Client()
    client.connect(hostname, port, 60)
    check_and_publish(sensor, client)


if __name__ == "__main__":
    while True:
        main()
