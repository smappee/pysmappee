Official Smappee Python Library
===============================

Python Library for the Smappee dev API (v3) and MQTT interface.

Version
-------

0.0.1

Installation
------------
The recommended way to install is via [pip](https://pypi.org/) (comming soon)

    $ pip3 install pysmappee

Getting Started
---------------
Before we can use PySmappee, we need to be authenticated to the Smappee cloud.
The authentication mechanism is based on oauth2 specification,
for more information on the oauth2 spec see [http://oauth.net/documentation](http://oauth.net/documentation).
We need to register our application with Smappee by contacting [info@smappee.com](mailto:info@smappee.com).


### Smappee
When we registered our application we got a `client_id` and `client_secret`.
Together with our Smappee `username` and `password` we can create an instance of the Smappee class which automatically creates and API instance.

```python
from pysmappee import Smappee
smappee = Smappee(username, password, client_id, client_secret)
```

The `load_configuration` method loads all shared service locations our user has access to the `service_locations` property and iteratively collects all service location details.

```python
smappee.load_configuration()
smappee.service_locations  # dictionary holding all shared service locations instances
```

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
An appliance instance holds the appliance id, name and type
```python
appl = smappee.service_locations.get(12345).appliances  # where 12345 should be the correct servie location id
for appliance_id, appliance in appl.items():
    appliance.id
    appliance.name
    appliance.type
```

### Actuators
An actuator instance holds the actuator id, name, type, serialnumber, current state and todays energy consumption
```python
acts = smappee.service_locations.get(12345).actuators  # where 12345 should be the correct servie location id
for actuator_id, actuator in acts.items():
    actuator.id
    actuator.name
    actuator.type
    actuator.serialnumber
    actuator.state
    actuator.consumption_today
```

### Sensors

### Measurements

### Realtime values

### Aggregated values

Changelog
---------
0.0.1
* Initial commit

Support
-------
If you find a bug, have any questions about how to use PySmappee or have suggestions for improvements then feel free to file an issue on the `Github project page <https://github.com/smappee/pysmappee>`_.

License
-------
(MIT License)

