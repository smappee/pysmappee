from datetime import datetime, timedelta
from .mqtt import SmappeeMqtt
from .actuator import SmappeeActuator
from .appliance import SmappeeAppliance
from .measurement import SmappeeMeasurement
from .sensor import SmappeeSensor
from .smart_device import SmappeeSmartDevice
from cachetools import TTLCache


class SmappeeServiceLocation(object):

    def __init__(self, device_serial_number, smappee_api, service_location_id=None, local_polling=False):
        # service location details
        self._service_location_id = service_location_id
        self._device_serial_number = device_serial_number
        self._phase_type = None
        self._has_solar_production = False
        self._has_voltage_values = False
        self._has_reactive_value = False
        self._firmware_version = None

        # api instance to (re)load consumption data
        self.smappee_api = smappee_api
        self._local_polling = local_polling

        # mqtt connections
        self.mqtt_connection_central = None
        self.mqtt_connection_local = None

        # coordinates
        self._latitude = None
        self._longitude = None
        self._timezone = None

        # presence
        self._presence = None

        # dicts to hold appliances, smart switches, ct details and smart devices by id
        self._appliances = {}
        self._actuators = {}
        self._sensors = {}
        self._measurements = {}
        self._smart_devices = {}

        # realtime values
        self._realtime_values = {
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
        self._aggregated_values = {
            'power_today': None,
            'power_current_hour': None,
            'power_last_5_minutes': None,
            'solar_today': None,
            'solar_current_hour': None,
            'solar_last_5_minutes': None,
            'alwayson_today': None,
            'alwayson_current_hour': None,
            'alwasyon_last_5_minutes': None
        }

        self._cache = TTLCache(maxsize=100, ttl=300)

        self.load_configuration()

        self.update_trends_and_appliance_states()

    def load_configuration(self, refresh=False):
        # Set solar production on 11-series (no measurements config available on non 50-series)
        if self._device_serial_number.startswith('11'):
            self.has_solar_production = True

        # Set voltage values on 5-series
        if self._device_serial_number.startswith('50') or self._device_serial_number.startswith('51'):
            self.has_voltage_values = True

        if self.local_polling:
            self._service_location_name = f'Smappee {self.device_serial_number} local'
            self._service_location_uuid = 0

            if self._device_serial_number.startswith('50'):
                self._has_reactive_value = True
                self._phase_type = self.smappee_api.phase_type
            else:
                # Load actuators
                self.smappee_api.logon()
                command_control_config = self.smappee_api.load_command_control_config()
                if command_control_config is not None:
                    for ccc in command_control_config:
                        if ccc.get('type') == '2':
                            at = 'COMFORT_PLUG'
                        elif ccc.get('type') == '3':
                            at = 'SWITCH'
                        else:
                            # Unknown actuator type
                            continue
                        self._add_actuator(id=int(ccc.get('key')),
                                           name=ccc.get('value'),
                                           serialnumber=ccc.get('serialNumber'),
                                           state_values=[
                                               {'id': 'ON_ON', 'name': 'on', 'current': ccc.get('relayStatus') is True},
                                               {'id': 'OFF_OFF', 'name': 'off', 'current': ccc.get('relayStatus') is False}],
                                           connection_state=ccc.get('connectionStatus').upper() if 'connectionStatus' in ccc else None,
                                           actuator_type=at)

                # Load channels config pro Smappee11 and 2-series and only
                if self._device_serial_number.startswith('11'):
                    self.smappee_api.load_config()
                elif self._device_serial_number.startswith('2'):
                    channels_config = self.smappee_api.load_channels_config()
                    for input_channel in channels_config['inputChannels']:
                        if input_channel['inputChannelType'] == 'PRODUCTION' and input_channel['inputChannelConnection'] == 'GRID':
                            self.has_solar_production = True

        else:
            # Collect metering configuration
            sl_metering_configuration = self.smappee_api.get_metering_configuration(service_location_id=self.service_location_id)

            # Service location details
            self._service_location_name = sl_metering_configuration.get('name')
            self._service_location_uuid = sl_metering_configuration.get('serviceLocationUuid')

            # Set coordinates and timezone
            self.latitude = sl_metering_configuration.get('lat')
            self.longitude = sl_metering_configuration.get('lon')
            self.timezone = sl_metering_configuration.get('timezone')

            # Load appliances
            for appliance in sl_metering_configuration.get('appliances'):
                if appliance.get('type') != 'Find me' and appliance.get('sourceType') == 'NILM':
                    self._add_appliance(id=appliance.get('id'),
                                        name=appliance.get('name'),
                                        type=appliance.get('type'),
                                        source_type=appliance.get('sourceType'))

            # Load actuators (Smappee Switches, Comfort Plugs, IO modules)
            for actuator in sl_metering_configuration.get('actuators'):
                self._add_actuator(id=actuator.get('id'),
                                   name=actuator.get('name'),
                                   serialnumber=actuator.get('serialNumber') if 'serialNumber' in actuator else None,
                                   state_values=actuator.get('states'),
                                   connection_state=actuator.get('connectionState'),
                                   actuator_type=actuator.get('type'))

            # Load sensors (Smappee Gas and Water)
            for sensor in sl_metering_configuration.get('sensors'):
                self._add_sensor(id=sensor.get('id'),
                                 name=sensor.get('name'),
                                 channels=sensor.get('channels'))

            # Set phase type
            self.phase_type = sl_metering_configuration.get('phaseType') if 'phaseType' in sl_metering_configuration else None

            # Load channel configuration
            if 'measurements' in sl_metering_configuration:
                for measurement in sl_metering_configuration.get('measurements'):
                    self._add_measurement(id=measurement.get('id'),
                                          name=measurement.get('name'),
                                          type=measurement.get('type'),
                                          subcircuitType=measurement.get('subcircuitType') if 'subcircuitType' in measurement else None,
                                          channels=measurement.get('channels'))

                    if measurement.get('type') == 'PRODUCTION':
                        self.has_solar_production = True

            # Setup MQTT connection
            if not refresh:
                self.mqtt_connection_central = self.load_mqtt_connection(kind='central')

                # Only use a local MQTT broker for 20# or 50# series monitors
                if self._device_serial_number.startswith('20') or self._device_serial_number.startswith('50'):
                    self.mqtt_connection_local = self.load_mqtt_connection(kind='local')
                    self.has_reactive_value = True  # reactive only available through local MQTT

    @property
    def service_location_id(self):
        return self._service_location_id

    @property
    def service_location_uuid(self):
        return self._service_location_uuid

    @property
    def service_location_name(self):
        return self._service_location_name

    @service_location_name.setter
    def service_location_name(self, name):
        self._service_location_name = name

    @property
    def device_serial_number(self):
        return self._device_serial_number

    @property
    def device_model(self):
        model_mapping = {
            '10': 'Energy',
            '11': 'Solar',
            '20': 'Pro/Plus',
            '50': 'Genius',
            '5100': 'Wi-Fi Connect',
            '5110': 'Wi-Fi Connect',
            '5130': 'Ethernet Connect',
            '5140': '4G Connect',
            '57': 'P1S1 module',
        }
        if self.device_serial_number is None:
            return 'Smappee deactivated'
        elif self.device_serial_number[:2] in model_mapping:
            return f'Smappee {model_mapping[self.device_serial_number[:2]]}'
        elif self.device_serial_number[:4] in model_mapping:
            return f'Smappee {model_mapping[self.device_serial_number[:4]]}'
        else:
            'Smappee'

    @property
    def phase_type(self):
        return self._phase_type

    @phase_type.setter
    def phase_type(self, phase_type):
        self._phase_type = phase_type

    @property
    def has_solar_production(self):
        return self._has_solar_production

    @has_solar_production.setter
    def has_solar_production(self, has_solar_production):
        self._has_solar_production = has_solar_production

    @property
    def has_voltage_values(self):
        return self._has_voltage_values

    @has_voltage_values.setter
    def has_voltage_values(self, has_voltage_values):
        self._has_voltage_values = has_voltage_values

    @property
    def has_reactive_value(self):
        return self._has_reactive_value

    @has_reactive_value.setter
    def has_reactive_value(self, has_reactive_value):
        self._has_reactive_value = has_reactive_value

    @property
    def local_polling(self):
        return self._local_polling

    @property
    def latitude(self):
        return self._latitude

    @latitude.setter
    def latitude(self, lat):
        self._latitude = lat

    @property
    def longitude(self):
        return self._longitude

    @longitude.setter
    def longitude(self, lon):
        self._longitude = lon

    @property
    def timezone(self):
        return self._timezone

    @timezone.setter
    def timezone(self, timezone):
        self._timezone = timezone

    @property
    def firmware_version(self):
        return self._firmware_version

    @firmware_version.setter
    def firmware_version(self, firmware_version):
        self._firmware_version = firmware_version

    @property
    def is_present(self):
        return self._presence

    @is_present.setter
    def is_present(self, presence):
        self._presence = presence

    @property
    def appliances(self):
        return self._appliances

    def _add_appliance(self, id, name, type, source_type):
        self.appliances[id] = SmappeeAppliance(id=id,
                                               name=name,
                                               type=type,
                                               source_type=source_type)

    def update_appliance_state(self, id, delta=1440):
        if f"appliance_{id}" in self._cache:
            return

        end = datetime.utcnow()
        start = end - timedelta(minutes=delta)

        events = self.smappee_api.get_events(service_location_id=self.service_location_id,
                                             appliance_id=id,
                                             start=start,
                                             end=end)
        self._cache[f"appliance_{id}"] = events
        if events:
            power = abs(events[0].get('activePower'))
            self.appliances[id].power = power
            if 'state' in events[0]:
                # program appliance
                self.appliances[id].state = events[0].get('state') > 0
            else:
                # delta appliance
                self.appliances[id].state = events[0].get('activePower') > 0

    @property
    def actuators(self):
        return self._actuators

    def _add_actuator(self, id, name, serialnumber, state_values, connection_state, actuator_type):
        self.actuators[id] = SmappeeActuator(id=id,
                                             name=name,
                                             serialnumber=serialnumber,
                                             state_values=state_values,
                                             connection_state=connection_state,
                                             type=actuator_type)

        if not self.local_polling:
            # Get actuator state
            state = self.smappee_api.get_actuator_state(service_location_id=self.service_location_id,
                                                        actuator_id=id)
            self.actuators.get(id).state = state

            # Get actuator connection state (COMFORT_PLUG is always UNREACHABLE)
            connection_state = self.smappee_api.get_actuator_connection_state(service_location_id=self.service_location_id,
                                                                              actuator_id=id)
            connection_state = connection_state.replace('"', '')
            self.actuators.get(id).connection_state = connection_state

    def set_actuator_state(self, id, state, since=None, api=True):
        if id in self.actuators:
            if api:
                self.smappee_api.set_actuator_state(service_location_id=self.service_location_id,
                                                    actuator_id=id,
                                                    state_id=state)
            self.actuators.get(id).state = state

    def set_actuator_connection_state(self, id, connection_state, since=None):
        if id in self.actuators:
            self.actuators.get(id).connection_state = connection_state

    @property
    def sensors(self):
        return self._sensors

    def _add_sensor(self, id, name, channels):
        self.sensors[id] = SmappeeSensor(id, name, channels)

    @property
    def measurements(self):
        return self._measurements

    def _add_measurement(self, id, name, type, subcircuitType, channels):
        self.measurements[id] = SmappeeMeasurement(id=id,
                                                   name=name,
                                                   type=type,
                                                   subcircuit_type=subcircuitType,
                                                   channels=channels)

    @property
    def smart_devices(self):
        return self._smart_devices

    def _add_smart_device(self, uuid, name, category, implementation, minCurrent, maxCurrent, measurements):
        self.smart_devices[uuid] = SmappeeSmartDevice(uuid=uuid,
                                                      name=name,
                                                      category=category,
                                                      implementation=implementation,
                                                      minCurrent=minCurrent,
                                                      maxCurrent=maxCurrent,
                                                      measurements=measurements)

    @property
    def total_power(self):
        return self._realtime_values.get('total_power')

    @total_power.setter
    def total_power(self, value):
        self._realtime_values['total_power'] = value

    @property
    def total_reactive_power(self):
        return self._realtime_values.get('total_reactive_power')

    @total_reactive_power.setter
    def total_reactive_power(self, value):
        self._realtime_values['total_reactive_power'] = value

    @property
    def solar_power(self):
        return self._realtime_values.get('solar_power')

    @solar_power.setter
    def solar_power(self, value):
        self._realtime_values['solar_power'] = value

    @property
    def alwayson(self):
        return self._realtime_values.get('alwayson')

    @alwayson.setter
    def alwayson(self, value):
        self._realtime_values['alwayson'] = value

    @property
    def phase_voltages(self):
        return self._realtime_values.get('phase_voltages')

    @phase_voltages.setter
    def phase_voltages(self, values):
        self._realtime_values['phase_voltages'] = values

    @property
    def phase_voltages_h3(self):
        return self._realtime_values.get('phase_voltages_h3')

    @phase_voltages_h3.setter
    def phase_voltages_h3(self, values):
        self._realtime_values['phase_voltages_h3'] = values

    @property
    def phase_voltages_h5(self):
        return self._realtime_values.get('phase_voltages_h5')

    @phase_voltages_h5.setter
    def phase_voltages_h5(self, values):
        self._realtime_values['phase_voltages_h5'] = values

    @property
    def line_voltages(self):
        return self._realtime_values.get('line_voltages')

    @line_voltages.setter
    def line_voltages(self, values):
        self._realtime_values['line_voltages'] = values

    @property
    def line_voltages_h3(self):
        return self._realtime_values.get('line_voltages_h3')

    @line_voltages_h3.setter
    def line_voltages_h3(self, values):
        self._realtime_values['line_voltages_h3'] = values

    @property
    def line_voltages_h5(self):
        return self._realtime_values.get('line_voltages_h5')

    @line_voltages_h5.setter
    def line_voltages_h5(self, values):
        self._realtime_values['line_voltages_h5'] = values

    def load_mqtt_connection(self, kind):
        mqtt_connection = SmappeeMqtt(service_location=self,
                                      kind=kind,
                                      farm=self.smappee_api.farm)
        mqtt_connection.start()
        return mqtt_connection

    def _update_power_data(self, power_data):
        # use incoming power data (through central MQTT connection)
        self.total_power = power_data.get('consumptionPower')
        self.solar_power = power_data.get('solarPower')
        self.alwayson = power_data.get('alwaysOn')

        if 'phaseVoltageData' in power_data:
            self.phase_voltages = [pv / 10 for pv in power_data.get('phaseVoltageData')]
            self.phase_voltages_h3 = power_data.get('phaseVoltageH3Data')
            self.phase_voltages_h5 = power_data.get('phaseVoltageH5Data')

        if 'lineVoltageData' in power_data:
            self.line_voltages = [lv / 10 for lv in power_data.get('lineVoltageData')]
            self.line_voltages_h3 = power_data.get('lineVoltageH3Data')
            self.line_voltages_h5 = power_data.get('lineVoltageH5Data')

        if 'activePowerData' in power_data:
            active_power_data = power_data.get('activePowerData')
            for _, measurement in self.measurements.items():
                measurement.update_active(active=active_power_data)

        if 'reactivePowerData' in power_data:
            reactive_power_data = power_data.get('reactivePowerData')
            for _, measurement in self.measurements.items():
                measurement.update_reactive(reactive=reactive_power_data)

        if 'currentData' in power_data:
            current_data = power_data.get('currentData')
            for _, measurement in self.measurements.items():
                measurement.update_current(current=current_data)

        # update smart devices power
        # for uuid, smart_device in self.smart_devices.items():
        #     smart_device.update_active(active=active_power_data)
        #     smart_device.update_reactive(reactive=reactive_power_data)
        #     smart_device.update_current(current=current_data)

    def _update_realtime_data(self, realtime_data):
        # Use incoming realtime data (through local MQTT connection)
        self.total_power = realtime_data.get('totalPower')
        self.reactive_power = realtime_data.get('totalReactivePower')
        self.phase_voltages = realtime_data.get('voltages')

        active_power_data, current_data = {}, {}
        for channel_power in realtime_data.get('channelPowers'):
            active_power_data[channel_power.get('publishIndex')] = channel_power.get('power')
            current_data[channel_power.get('publishIndex')] = channel_power.get('current') / 10

        # update channel data
        for _, measurement in self.measurements.items():
            measurement.update_active(active=active_power_data, source='LOCAL')
            measurement.update_current(current=current_data, source='LOCAL')

    @property
    def aggregated_values(self):
        return self._aggregated_values

    def update_active_consumptions(self, trend='today'):
        params = {
            'today': {'aggtype': 3, 'delta': 1440},
            'current_hour': {'aggtype': 2, 'delta': 60},
            'last_5_minutes': {'aggtype': 1, 'delta': 9}
        }

        if f'total_consumption_{trend}' in self._cache:
            return

        end = datetime.utcnow()
        start = end - timedelta(minutes=params.get(trend).get('delta'))

        consumption_result = self.smappee_api.get_consumption(service_location_id=self.service_location_id,
                                                              start=start,
                                                              end=end,
                                                              aggregation=params.get(trend).get('aggtype'))
        self._cache[f'total_consumption_{trend}'] = consumption_result

        if consumption_result['consumptions']:
            self.aggregated_values[f'power_{trend}'] = consumption_result.get('consumptions')[0].get('consumption')
            self.aggregated_values[f'solar_{trend}'] = consumption_result.get('consumptions')[0].get('solar')
            self.aggregated_values[f'alwayson_{trend}'] = consumption_result.get('consumptions')[0].get('alwaysOn') * 12

    def update_todays_actuator_consumptions(self, aggtype=3, delta=1440):
        end = datetime.utcnow()
        start = end - timedelta(minutes=delta)

        for id, actuator in self.actuators.items():
            if f'actuator_{id}_consumption_today' in self._cache:
                continue

            consumption_result = self.smappee_api.get_switch_consumption(service_location_id=self.service_location_id,
                                                                         switch_id=id,
                                                                         start=start,
                                                                         end=end,
                                                                         aggregation=aggtype)
            self._cache[f'actuator_{id}_consumption_today'] = consumption_result

            if consumption_result['records']:
                actuator.consumption_today = consumption_result.get('records')[0].get('active')

    def update_todays_sensor_consumptions(self, aggtype=3, delta=1440):
        end = datetime.utcnow()
        start = end - timedelta(minutes=delta)

        for id, sensor in self.sensors.items():
            if f'sensor_{id}_consumption_today' in self._cache:
                continue

            consumption_result = self.smappee_api.get_sensor_consumption(service_location_id=self.service_location_id,
                                                                         sensor_id=id,
                                                                         start=start,
                                                                         end=end,
                                                                         aggregation=aggtype)
            self._cache[f'sensor_{id}_consumption_today'] = consumption_result

            if consumption_result['records']:
                sensor.update_today_values(record=consumption_result.get('records')[0])

                if 'temperature' in consumption_result.get('records')[0]:
                    sensor.temperature = consumption_result.get('records')[0].get('temperature')

                if 'humidity' in consumption_result.get('records')[0]:
                    sensor.humidity = consumption_result.get('records')[0].get('humidity')

                if 'battery' in consumption_result.get('records')[0]:
                    sensor.battery = consumption_result.get('records')[0].get('battery')

    def update_trends_and_appliance_states(self, ):
        if self.local_polling and self._device_serial_number.startswith('50'):
            self._realtime_values['total_power'] = self.smappee_api.realtime.get('totalPower', 0)
            self._realtime_values['total_reactive_power'] = self.smappee_api.realtime.get('totalReactivePower', 0)
            self._realtime_values['phase_voltages'] = [v.get('voltage', 0) for v in self.smappee_api.realtime.get('voltages', [{}, {}, {}])]

        elif self.local_polling:
            # Active power
            tp = self.smappee_api.active_power()
            if tp is not None:
                self._realtime_values['total_power'] = tp

            # Solar power
            if self.has_solar_production:
                sp = self.smappee_api.active_power(solar=True)
                if sp is not None:
                    self._realtime_values['solar_power'] = sp
        else:
            # update trend consumptions
            self.update_active_consumptions(trend='today')
            self.update_active_consumptions(trend='current_hour')
            self.update_active_consumptions(trend='last_5_minutes')
            self.update_todays_sensor_consumptions()
            self.update_todays_actuator_consumptions()

            # update appliance states
            for appliance_id, _ in self.appliances.items():
                self.update_appliance_state(id=appliance_id)
