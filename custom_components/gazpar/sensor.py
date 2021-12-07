from datetime import timedelta, datetime
import logging
import traceback

from custom_components.gazpar.gazpar import Gazpar
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity, STATE_CLASS_TOTAL_INCREASING
from homeassistant.const import (
    CONF_PASSWORD, CONF_USERNAME,
    VOLUME_CUBIC_METERS, ENERGY_KILO_WATT_HOUR, DEVICE_CLASS_ENERGY, DEVICE_CLASS_GAS))
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import track_time_interval, call_later

_LOGGER = logging.getLogger(__name__)

# CONST
DEFAULT_SCAN_INTERVAL = timedelta(hours=4)

CONF_PCE = 'pce'

# Sensors
HA_INDEX_ENERGY_M3 = 'Gazpar m3'
HA_INDEX_ENERGY_KWH = 'Gazpar kwh'

# Attributes
ATTR_JOURNEE_GAZIERE = 'Journee gaziere'

# Config
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_PCE): cv.string,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Configure the platform and add the Gazpar sensor."""

    _LOGGER.debug('Initializing Gazpar platform...')

    try:
        username = config[CONF_USERNAME]
        password = config[CONF_PASSWORD]
        pce = config[CONF_PCE]

        account = GazparAccount(hass, username, password, pce)
        add_entities(account.sensors, True)

        _LOGGER.debug('Gazpar platform initialization has completed successfully')
    except BaseException:
        _LOGGER.error('Gazpar platform initialization has failed with exception : {0}'.format(traceback.format_exc()))


class GazparAccount:
    """Representation of a Gazpar account."""

    def __init__(self, hass, username, password, pce):
        """Initialise the Gazpar account."""
        self._username = username
        self._password = password
        self._pce = pce
        self.sensors = []

        call_later(hass, 5, self.update_gazpar_data)

        # Add sensors
        self.sensors.append(GazparSensor(HA_INDEX_ENERGY_KWH, ENERGY_KILO_WATT_HOUR, DEVICE_CLASS_ENERGY))
        self.sensors.append(GazparSensor(HA_INDEX_ENERGY_M3, VOLUME_CUBIC_METERS, DEVICE_CLASS_GAS))

        track_time_interval(hass, self.update_gazpar_data, DEFAULT_SCAN_INTERVAL)

    def update_gazpar_data(self, event_time):
        """Fetch new state data for the sensor."""
        _LOGGER.debug('Querying Gazpar library for new data...')

        try:
            # Get full month data
            gazpar = Gazpar(self._username, self._password, self._pce)
            index_m3, index_kwh = gazpar.get_consumption()

            # Update sensors
            for sensor in self.sensors:
                if sensor.name == HA_INDEX_ENERGY_M3:
                    sensor.set_data(index_m3)
                    sensor.set_attributes(journeeGaziere)
                if sensor.name == HA_INDEX_ENERGY_KWH:
                    sensor.set_data(index_kwh)

                sensor.async_schedule_update_ha_state(True)
                _LOGGER.debug('Gazpar data updatede')
        except BaseException:
            _LOGGER.error('Failed to query Gazpar library with exception : {0}'.format(traceback.format_exc()))

    @property
    def username(self):
        """Return the username."""
        return self._username


class GazparSensor(SensorEntity):
    """Representation of a sensor entity for Gazpar."""

    def __init__(self, name, unit, device_class):
        """Initialize the sensor."""
        self._name = name
        self._unit = unit
        self._measure = None
        self._attr_state_class = STATE_CLASS_TOTAL_INCREASING
        self._attr_device_class = device_class
        self._extra_state_attributes = {}


    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._measure

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return 'mdi:fire'

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        return self._extra_state_attributes

    def set_data(self, measure):
        """Update sensor data"""
        self._measure = measure

    def set_attributes(self, attr):
        """Return the state attributes of the last update."""
        attrs = {}

        if self._measure is not None:
            attrs[ATTR_JOURNEE_GAZIERE] = attr
            self._extra_state_attributes = attrs

