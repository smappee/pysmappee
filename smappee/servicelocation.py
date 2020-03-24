from datetime import datetime, timedelta
from .mqtt import SmappeeMqtt
from .actuator import SmappeeActuator
from .appliance import SmappeeAppliance
from .measurement import SmappeeMeasurement
from .sensor import SmappeeSensor
from .smart_device import SmappeeSmartDevice
from cachetools import TTLCache


class SmappeeServiceLocation(object):

    def __init__(self, service_location_id, service_location_uuid, name, device_serial_number, smappee_api):
        # service location details
        self.service_location_id = service_location_id
        self.service_location_uuid = service_location_uuid
        self.service_location_name = name
        self.device_serial_number = device_serial_number
        self.phase_type = None
        self.has_solar = False
        self.firmware_version = None

        # api instance to (re)load consumption data
        self.smappee_api = smappee_api

        # mqtt connections
        self.mqtt_connection_central = None
        self.mqtt_connection_local = None

        # coordinates
        self.lat = None
        self.lon = None
        self.timezone = None

        # presence
        self.presence = None

        # dicts to hold appliances, smart switches, ct details and smart devices by id
        self.appliances = {}
        self.actuators = {}
        self.sensors = {}
        self.measurements = {}
        self.smart_devices = {}

        # realtime values
        self.realtime_values = {
            'total_power': None,
            'total_reactive_power': None,
            'solar_power': None,
            'alwayson': None,
            'phase_voltages': None,
            'phase_voltages_h3': None,
            'phase_voltages_h5': None,
            'line_voltages': None,
            'line_voltages_h3': None,
            'line_voltages_h5': None,
        }

        # extracted consumption values
        self.aggregated_values = {
            'power_today': None,
            'power_last_hour': None,
            'power_last_5_minutes': None,
            'solar_today': None,
            'solar_last_hour': None,
            'solar_last_5_minutes': None,
            'alwayson_today': None,
            'alwayson_last_hour': None,
            'alwasyon_last_5_minutes': None
        }

        self.cache = TTLCache(maxsize=100, ttl=600)

        self.load_configuration()

        self.update_trends_and_appliance_states()

    def load_configuration(self, refresh=False):
        # Collect service location info
        sl_info = self.smappee_api.get_service_location_info(service_location_id=self.service_location_id)

        # Collect metering configuration
        sl_metering_configuration = self.smappee_api.get_metering_configuration(service_location_id=self.service_location_id)

        # Service location details
        self.set_service_location_name(service_location_name=sl_metering_configuration['name'])

        # Set coordinates and timezone
        self.set_coordinates(lat=sl_metering_configuration['lat'],
                             lon=sl_metering_configuration['lon'])
        self.set_timezone(timezone=sl_metering_configuration['timezone'])

        # Load appliances
        for appliance in sl_metering_configuration['appliances']:
            self.add_appliance(id=appliance['id'],
                               name=appliance['name'],
                               type=appliance['type'])

        # Load actuators (Smappee Switches, Comfort Plugs, IO modules)
        for actuator in sl_metering_configuration['actuators']:
            self.add_actuator(id=actuator['id'],
                              name=actuator['name'],
                              actuator_type=actuator['type'] if 'type' in actuator else 'CCD_LEAF_LITE')

        # Load sensors (Smappee Gas and Water)
        for sensor in sl_metering_configuration['sensors']:
            self.add_sensor(id=sensor['id'],
                            name=sensor['name'],
                            channels=sensor['channels'])

        # Set phase type
        self.phase_type = sl_metering_configuration['phaseType'] if 'phaseType' in sl_metering_configuration else None

        # Load channel configuration
        if 'measurements' in sl_metering_configuration:
            for measurement in sl_metering_configuration['measurements']:
                self.add_measurement(id=measurement['id'],
                                     name=measurement['name'],
                                     type=measurement['type'],
                                     subcircuitType=measurement['subcircuitType'] if 'subcircuitType' in measurement else None,
                                     channels=measurement['channels'])

                if measurement['type'] == 'PRODUCTION':
                    self.has_solar = True

        # Setup MQTT connection
        if not refresh:
            self.mqtt_connection_central = self.load_mqtt_connection(kind='central')
            self.mqtt_connection_local = self.load_mqtt_connection(kind='local')

    def set_service_location_name(self, service_location_name):
        self.service_location_name = service_location_name

    def get_service_location_name(self):
        return self.service_location_name

    def get_service_location_id(self):
        return self.service_location_id

    def get_service_location_uuid(self):
        return self.service_location_uuid

    def get_device_model(self):
        model_mapping = {
            '10': 'Smappee Energy',
            '11': 'Smappee Solar',
            '20': 'Smappee Pro/Plus',
            '50': 'Smappee Genius',
            '51': 'Smappee Connect',
            '57': 'Smappee P1S1 module',
        }
        if self.device_serial_number[:2] in model_mapping:
            return model_mapping[self.device_serial_number[:2]]
        else:
            'Smappee'

    def get_device_serial_number(self):
        return self.device_serial_number

    def get_phase_type(self):
        return self.phase_type

    def has_solar_production(self):
        return self.has_solar

    def set_coordinates(self, lat, lon):
        self.lat, self.lon = lat, lon

    def get_coordinates(self):
        return self.lat, self.lon

    def set_timezone(self, timezone):
        self.timezone = timezone

    def get_timezone(self):
        return self.timezone

    def set_firmware_version(self, firmware_version):
        self.firmware_version = firmware_version

    def get_firmware_version(self):
        return self.firmware_version

    def set_presence(self, presence):
        self.presence = presence

    def is_present(self):
        return self.presence

    def add_appliance(self, id, name, type):
        self.appliances[id] = SmappeeAppliance(id=id,
                                               name=name,
                                               type=type)

    def get_appliances(self):
        return self.appliances

    def update_appliance_state(self, id, delta=1440):
        if f"appliance_{id}" in self.cache:
            return

        end = datetime.utcnow()
        start = end - timedelta(minutes=delta)

        events = self.smappee_api.get_events(service_location_id=self.service_location_id,
                                             appliance_id=id,
                                             start=start,
                                             end=end)
        self.cache[f"appliance_{id}"] = events
        if events:
            power = abs(events[0]['activePower'])
            self.appliances[id].set_power(power=power)
            if 'state' in events[0]:
                # program appliance
                self.appliances[id].set_state(state=True if events[0]['state'] > 0 else False)
            else:
                # delta appliance
                self.appliances[id].set_state(state=True if events[0]['activePower'] > 0 else False)

    def add_actuator(self, id, name, actuator_type):
        type_mapping = {
            'CCD_CHACON_SIMPLE': 'PLUG',
            'CCD_ELRO_SIMPLE': 'PLUG',
            'CCD_HE_ADVANCED': 'PLUG',
            'CCD_LEAF_LITE': 'SWITCH',
            'INFINITY_OUTPUT_MODULE': 'OUTPUT_MODULE',
        }
        self.actuators[id] = SmappeeActuator(id=id,
                                             name=name,
                                             actuator_type=type_mapping[actuator_type])

        if self.actuators[id].actuator_type in ['SWITCH']:
            # Get actuator state
            state = self.smappee_api.get_actuator_state(service_location_id=self.service_location_id,
                                                        actuator_id=id)
            self.actuators[id].set_state(state=state)

    def get_actuators(self):
        return self.actuators

    def actuator_on(self, id):
        if id in self.actuators:
            self.smappee_api.actuator_on(service_location_id=self.service_location_id,
                                         actuator_id=id)
            self.actuators.get(id).set_state(state='ON')

    def actuator_off(self, id):
        if id in self.actuators:
            self.smappee_api.actuator_off(service_location_id=self.service_location_id,
                                          actuator_id=id)
            self.actuators.get(id).set_state(state='OFF')

    def set_actuator_state(self, id, state, since):
        if id in self.actuators:
            self.actuators[id].set_state(state=state)

    def set_actuator_connection_state(self, id, connection_state, since):
        if id in self.actuators:
            self.actuators[id].set_connection_state(connectionState=connection_state)

    def add_sensor(self, id, name, channels):
        self.sensors[id] = SmappeeSensor(id, name, channels)

    def get_sensors(self):
        return self.sensors

    def add_measurement(self, id, name, type, subcircuitType, channels):
        self.measurements[id] = SmappeeMeasurement(id=id,
                                                   name=name,
                                                   type=type,
                                                   subcircuitType=subcircuitType,
                                                   channels=channels)

    def get_measurements(self):
        return self.measurements

    def add_smart_device(self, uuid, name, category, implementation, minCurrent, maxCurrent, measurements):
        self.smart_devices[uuid] = SmappeeSmartDevice(uuid=uuid,
                                                      name=name,
                                                      category=category,
                                                      implementation=implementation,
                                                      minCurrent=minCurrent,
                                                      maxCurrent=maxCurrent,
                                                      measurements=measurements)

    def get_smart_devices(self):
        return self.smart_devices

    def load_mqtt_connection(self, kind):
        mqtt_connection = SmappeeMqtt(service_location=self,
                                      service_location_id=self.service_location_id,
                                      service_location_uuid=self.service_location_uuid,
                                      device_serial_number=self.device_serial_number,
                                      kind=kind)
        mqtt_connection.start()
        return mqtt_connection

    def update_power_data(self, power_data):
        # use incoming power data (through central MQTT connection)
        self.realtime_values['total_power'] = power_data['consumptionPower']
        self.realtime_values['solar_power'] = power_data['solarPower']
        self.realtime_values['alwayson'] = power_data['alwaysOn']

        if 'phaseVoltageData' in power_data:
            self.realtime_values['phase_voltages'] = [pv / 10 for pv in power_data['phaseVoltageData']]
            self.realtime_values['phase_voltages_h3'] = power_data['phaseVoltageH3Data']
            self.realtime_values['phase_voltages_h5'] = power_data['phaseVoltageH5Data']

        if 'lineVoltageData' in power_data:
            self.realtime_values['line_voltages'] = [lv / 10 for lv in power_data['lineVoltageData']]
            self.realtime_values['line_voltages_h3'] = power_data['lineVoltageH3Data']
            self.realtime_values['line_voltages_h5'] = power_data['lineVoltageH5Data']

        if 'activePowerData' in power_data:
            active_power_data = power_data['activePowerData']

        if 'reactivePowerData' in power_data:
            reactive_power_data = power_data['reactivePowerData']

        if 'currentData' in power_data:
            current_data = power_data['currentData']

        # update channel data
        for id, measurement in self.measurements.items():
            measurement.update_active(active=active_power_data)
            measurement.update_reactive(reactive=reactive_power_data)
            measurement.update_current(current=current_data)

        # update smart devices power
        # for uuid, smart_device in self.smart_devices.items():
        #     smart_device.update_active(active=active_power_data)
        #     smart_device.update_reactive(reactive=reactive_power_data)
        #     smart_device.update_current(current=current_data)

    def update_realtime_data(self, realtime_data):
        # Use incoming realtime data (through local MQTT connection)
        self.realtime_values['total_power'] = realtime_data['totalPower']
        self.realtime_values['reactive_power'] = realtime_data['totalReactivePower']
        self.realtime_values['phase_voltages'] = realtime_data['voltages']

        active_power_data, current_data = {}, {}
        for channel_power in realtime_data['channelPowers']:
            active_power_data[channel_power['publishIndex']] = channel_power['power']
            current_data[channel_power['publishIndex']] = channel_power['current'] / 10

        # update channel data
        for id, measurement in self.measurements.items():
            measurement.update_active(active=active_power_data, source='LOCAL')
            measurement.update_current(current=current_data, source='LOCAL')

    def update_active_consumptions(self, trend='today'):
        params = {
            'today': {'aggtype': 3, 'delta': 1440},
            'last_hour': {'aggtype': 2, 'delta': 120},
            'last_5_minutes': {'aggtype': 1, 'delta': 10}
        }

        if f'total_consumption_{trend}' in self.cache:
            return

        end = datetime.utcnow()
        start = end - timedelta(minutes=params[trend]['delta'])

        consumption_result = self.smappee_api.get_consumption(service_location_id=self.service_location_id,
                                                              start=start,
                                                              end=end,
                                                              aggregation=params[trend]['aggtype'])
        self.cache[f'total_consumption_{trend}'] = consumption_result

        if consumption_result['consumptions']:
            self.aggregated_values[f'power_{trend}'] = consumption_result['consumptions'][0]['consumption']
            self.aggregated_values[f'solar_{trend}'] = consumption_result['consumptions'][0]['solar']
            self.aggregated_values[f'alwayson_{trend}'] = consumption_result['consumptions'][0]['alwaysOn'] * 12

    def update_todays_actuator_consumptions(self, aggtype=3, delta=1440):
        end = datetime.utcnow()
        start = end - timedelta(minutes=delta)

        for id, actuator in self.actuators.items():
            if f'actuator_{id}_consumption_today' in self.cache:
                continue

            consumption_result = self.smappee_api.get_switch_consumption(service_location_id=self.service_location_id,
                                                                         switch_id=id,
                                                                         start=start,
                                                                         end=end,
                                                                         aggregation=aggtype)
            self.cache[f'actuator_{id}_consumption_today'] = consumption_result

            if consumption_result['records']:
                actuator.set_consumption_today(consumption_today=consumption_result['records'][0]['active'])

    def update_todays_sensor_consumptions(self, aggtype=3, delta=1440):
        end = datetime.utcnow()
        start = end - timedelta(minutes=delta)

        for id, sensor in self.sensors.items():
            if f'sensor_{id}_consumption_today' in self.cache:
                continue

            consumption_result = self.smappee_api.get_sensor_consumption(service_location_id=self.service_location_id,
                                                                         sensor_id=id,
                                                                         start=start,
                                                                         end=end,
                                                                         aggregation=aggtype)
            self.cache[f'sensor_{id}_consumption_today'] = consumption_result

            if consumption_result['records']:
                sensor.update_today_values(record=consumption_result['records'][0])

                if 'temperature' in consumption_result['records'][0]:
                    sensor.set_temperature(temperature=consumption_result['records'][0]['temperature'])

                if 'humidity' in consumption_result['records'][0]:
                    sensor.set_humidity(humidity=consumption_result['records'][0]['humidity'])

                if 'battery' in consumption_result['records'][0]:
                    sensor.set_battery(battery=consumption_result['records'][0]['battery'])

    def update_trends_and_appliance_states(self, ):
        # update trend consumptions
        self.update_active_consumptions(trend='today')
        self.update_active_consumptions(trend='last_hour')
        self.update_active_consumptions(trend='last_5_minutes')
        self.update_todays_sensor_consumptions()
        self.update_todays_actuator_consumptions()

        # update appliance states
        for appliance_id, appliance in self.appliances.items():
            self.update_appliance_state(id=appliance_id)

