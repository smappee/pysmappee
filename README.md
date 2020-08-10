Official Smappee Python Library
===============================

Python Library for the Smappee dev API (v3) and MQTT interface. Used as a wrapper dependency in the Home Assistant integration.

Version
-------

0.2.10

Installation
------------
The recommended way to install is via [pip](https://pypi.org/)

    $ pip3 install pysmappee

Getting Started
---------------
Before we can use PySmappee, we need to be authenticated to the Smappee cloud.
The authentication mechanism is based on OAuth2 specification,
for more information on the OAuth2 spec see [http://oauth.net/documentation](http://oauth.net/documentation).
We need to register our application with Smappee by contacting [info@smappee.com](mailto:info@smappee.com).

Examples / Quickstart
--------------------

Structure
---------
### Service location
A service location instance holds
* Service location id
* Service location uuid
* Service location name
* Device serial number
* Phase type
* Has solar production boolean
* Firmware version
* Latitude and longitude coordinates
* Timezone
* Presence boolean
* Appliances
* Actuators (Smappee Comfort Plug, Smappee Switch, Smappee Output Modules)
* Sensors (Smappee Gas and Water)
* Measurements (CT details)
* Realtime values
* Some predefined aggregated values

### Appliances
An appliance instance holds the appliance id, name, type and source type (NILM or CT appliance)
```python
appl = smappee.service_locations.get(12345).appliances  # where 12345 should be the correct servie location id
for appliance_id, appliance in appl.items():
    appliance.id
    appliance.name
    appliance.type
    appliance.source_type
```

### Actuators
An actuator instance holds the actuator id, name, type, serialnumber, current state, state options and todays energy consumption
```python
sl = smappee.service_locations.get(12345) # where 12345 should be the correct service location id
for actuator_id, actuator in sl.actuators.items():
    actuator.id
    actuator.name
    actuator.type
    actuator.serialnumber
    actuator.state
    actuator.state_options
    actuator.consumption_today
```

Changing the actuator state can be done with the `set_actuator_state` in the `service_location` class.
```python
# Example: turn OFF actuator with id 1 from service location 12345
sl = smappee.service_locations.get(12345) # where 12345 should be the correct service location id
sl.set_actuator_state(id=1, state='OFF')
```

### Sensors
A sensor instance holds the sensor id, name, channels, temperature, humidity and battery level.
```python
sl = smappee.service_locations.get(12345) # where 12345 should be the correct service location id
for sensor_id, sensor in sl.sensors.items():
    sensor.id
    sensor.name
    sensor.channels
    sensor.temperature
    sensor.humidity
    sensor.battery
```

### Measurements
A measurement reflects a CT load and holds information like measurement id, name, (sub)type, channels and live values
(active, reactive and current total).
```python
sl = smappee.service_locations.get(12345) # where 12345 should be the correct service location id
for measurement_id, measurement in sl.measurements.items():
    measurement.id
    measurement.name
    measurement.type
    measurement.subcircuit_type
    measurement.channels
    measurement.active_total
    measurement.reactive_total
    measurement.current_total
```

### Realtime values
Realtime values are collected through central and local MQTT connections and kept in the `service_location` class.
```python
sl = smappee.service_locations.get(12345) # where 12345 should be the correct service location id
sl.total_power
sl.total_reactive_power
sl.solar_power
sl.alwayson
sl.phase_voltages  # lists
sl.phase_voltages_h3
sl.phase_voltages_h5
sl.line_voltages
sl.line_voltages_h3
sl.line_voltages_h5
```

### Aggregated values
A predefined set of aggregated energy values are being saved in the `service_location` class. Reloading these values can
be done by using the `update_trends_and_appliance_states` method
```python
sl = smappee.service_locations.get(12345) # where 12345 should be the correct service location id
sl.update_trends_and_appliance_states()
aggr = sl.aggregated_values

aggr.get('power_today')
aggr.get('power_current_hour')
aggr.get('power_last_5_minutes')
aggr.get('solar_today')
aggr.get('solar_current_hour')
aggr.get('solar_last_5_minutes')
aggr.get('alwayson_today')
aggr.get('alwayson_current_hour')
aggr.get('alwayson_last_5_minutes')
```

Changelog
---------
0.0.1
* Initial commit

0.0.2
* Rename smappee directory

0.0.3
* Sync dev API

0.0.{4, 5, 6}
* Actuator connection state
* Platform option
* Measurement index check
* Location details source change

0.0.{7, 8, 9}
* Support comfort plug state change
* Add locations without active device
* Disable IO modules
* Align connection state values

0.1.{0, 1}
* Refactor api to work with implicit account linking
* Only keep farm variable in API class

0.1.{2, 3}
* Only use local MQTT for 20- and 50-series
* 11-series do have solar production

0.1.4
* Extend service location class with voltage and reactive bools
* Extend model mapping

0.1.5
* Catch expired token as an HTTPError

0.2.{0, .., 9}
* Implement standalone local API
* Only create objects if the serialnumber is known
* Review local API exception handling

0.2.10
* Phase 2 Local API (support Smappee Pro/Plus)
* Local API improvements (Switch current status, cache load)

Support
-------
If you find a bug, have any questions about how to use PySmappee or have suggestions for improvements then feel free to 
file an issue on the GitHub project page [https://github.com/smappee/pysmappee](https://github.com/smappee/pysmappee).

License
-------
(MIT License)

