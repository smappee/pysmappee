"""Support for cloud and local Smappee MQTT."""
import json
import threading
import socket
import time
import traceback
import schedule
import uuid
from functools import wraps
import paho.mqtt.client as mqtt
from .config import config


TRACKING_INTERVAL = 60 * 5
HEARTBEAT_INTERVAL = 60 * 1


def tracking(func):
    # Decorator to reactivate trackers
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        if self._kind == 'central':
            if time.time() - self._last_tracking > TRACKING_INTERVAL:
                self._publish_tracking()
            if time.time() - self._last_heartbeat > HEARTBEAT_INTERVAL:
                self._publish_heartbeat()
        return func(*args, **kwargs)
    return wrapper


class SmappeeMqtt(threading.Thread):
    """Smappee MQTT wrapper."""

    def __init__(self, service_location, kind, farm):
        self._client = None
        self._service_location = service_location
        self._kind = kind
        self._farm = farm
        self._client_id = f"pysmappee-{self._service_location.service_location_uuid}-{self._kind}-{uuid.uuid4()}"
        self._last_tracking = 0
        self._last_heartbeat = 0
        threading.Thread.__init__(
            self,
            name=f'SmappeeMqttListener_{self._service_location.service_location_uuid}'
        )

    @property
    def topic_prefix(self):
        return f'servicelocation/{self._service_location.service_location_uuid}'

    @tracking
    def _on_connect(self, client, userdata, flags, rc):
        if self._kind == 'local':
            self._client.subscribe(topic='#')
        else:
            self._client.subscribe(topic=f'{self.topic_prefix}/#')
            self._schedule_tracking_and_heartbeat()

    def _schedule_tracking_and_heartbeat(self):
        schedule.every(60).seconds.do(lambda: self._publish_tracking())
        schedule.every(60).seconds.do(lambda: self._publish_heartbeat())

    def _publish_tracking(self):
        # turn OFF current tracking and restore
        self._client.publish(
            topic=f"{self.topic_prefix}/tracking",
            payload=json.dumps({
                "value": "OFF",
                "clientId": self._client_id,
                "serialNumber": self._service_location.device_serial_number,
                "type": "RT_VALUES",
            })
        )
        time.sleep(2)
        self._client.publish(
            topic=f"{self.topic_prefix}/tracking",
            payload=json.dumps({
                "value": "ON",
                "clientId": self._client_id,
                "serialNumber": self._service_location.device_serial_number,
                "type": "RT_VALUES",
            })
        )
        self._last_tracking = time.time()

    def _publish_heartbeat(self):
        self._client.publish(
            topic=f"{self.topic_prefix}/homeassistant/heartbeat",
            payload=json.dumps({
                "serviceLocationId": self._service_location.service_location_id,
            })
        )
        self._last_heartbeat = time.time()

    def _on_disconnect(self, client, userdata, rc):
        pass

    @tracking
    def _on_message(self, client, userdata, message):
        try:
            #print('{0} - Processing {1} MQTT message from topic {2} with value {3}'.format(self._service_location.service_location_id, self._kind, message.topic, message.payload))
            # realtime central power values
            if message.topic == f'{self.topic_prefix}/power':
                power_data = json.loads(message.payload)
                self._service_location._update_power_data(power_data=power_data)
            # realtime local power values
            elif message.topic == f'{self.topic_prefix}/realtime':
                realtime_data = json.loads(message.payload)
                self._service_location._update_realtime_data(realtime_data=realtime_data)
            # powerquality
            elif message.topic == f'{self.topic_prefix}/powerquality':
                pass

            # tracking and heartbeat
            elif message.topic == f'{self.topic_prefix}/tracking':
                pass
            elif message.topic == f'{self.topic_prefix}/homeassistant/heartbeat':
                pass

            # config topics
            elif message.topic == f'{self.topic_prefix}/config':
                config_details = json.loads(message.payload)
                self._service_location.firmware_version = config_details.get('firmwareVersion')
                self._service_location._service_location_uuid = config_details.get('serviceLocationUuid')
                self._service_location._service_location_id = config_details.get('serviceLocationId')
            elif message.topic == f'{self.topic_prefix}/sensorConfig':
                pass
            elif message.topic == f'{self.topic_prefix}/homeControlConfig':
                pass

            # aggregated consumption values
            elif message.topic == f'{self.topic_prefix}/aggregated':
                pass

            # presence topic
            elif message.topic == f'{self.topic_prefix}/presence':
                presence = json.loads(message.payload)
                self._service_location.is_present = presence.get('value')

            # trigger topic
            elif message.topic == f'{self.topic_prefix}/trigger':
                pass
            elif message.topic == f'{self.topic_prefix}/trigger/appliance':
                pass
            elif message.topic == f'{self.topic_prefix}/triggerpush':
                pass
            elif message.topic == f'{self.topic_prefix}/triggervalue':
                pass

            # harmonic vectors
            elif message.topic == f'{self.topic_prefix}/h1vector':
                pass

            # nilm
            elif message.topic == f'{self.topic_prefix}/nilm':
                pass

            # controllable nodes (general messages)
            elif message.topic == f'{self.topic_prefix}':
                msg = json.loads(message.payload)

                # turn ON/OFF comfort plug
                if msg.get('messageType') == 1283:
                    id = msg['content']['controllableNodeId']
                    plug_state = msg['content']['action']
                    plug_state_since = int(msg['content']['timestamp'] / 1000)
                    self._service_location.set_actuator_state(id=id,
                                                              state=plug_state,
                                                              since=plug_state_since,
                                                              api=False)

            # smart device and ETC topics
            elif message.topic.startswith(f'{self.topic_prefix}/etc/'):
                pass

            # specific HASS.io topics
            elif message.topic == f'{self.topic_prefix}/homeassistant/event':
                pass
            elif message.topic == f'{self.topic_prefix}/homeassistant/trigger/etc':
                pass
            elif message.topic.startswith(f'{self.topic_prefix}/outputmodule/'):
                pass
            elif message.topic == f'{self.topic_prefix}/scheduler':
                pass

            # actuator topics
            elif message.topic.startswith(f'{self.topic_prefix}/plug/'):
                plug_id = int(message.topic.split('/')[-2])
                payload = json.loads(message.payload)
                plug_state, plug_state_since = payload.get('value'), payload.get('since')

                state_type = message.topic.split('/')[-1]
                if state_type == 'state' and self._kind == 'central':  # todo: remove and condition
                    self._service_location.set_actuator_state(id=plug_id,
                                                              state=plug_state,
                                                              since=plug_state_since,
                                                              api=False)
                elif state_type == 'connectionState':
                    self._service_location.set_actuator_connection_state(id=plug_id,
                                                                         connection_state=plug_state,
                                                                         since=plug_state_since)
            elif config['MQTT']['discovery']:
                print(message.topic, message.payload)
        except Exception:
            traceback.print_exc()

    def start(self):
        self._client = mqtt.Client(client_id=self._client_id)
        if self._kind == 'central':
            self._client.username_pw_set(username=self._service_location.service_location_uuid,
                                         password=self._service_location.service_location_uuid)
        self._client.on_connect = lambda client, userdata, flags, rc: self._on_connect(client, userdata, flags, rc)
        self._client.on_message = lambda client, userdata, message: self._on_message(client, userdata, message)
        self._client.on_disconnect = lambda client, userdata, rc: self._on_disconnect(client, userdata, rc)

        #  self._client.tls_set(None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1)
        if self._kind == 'central':
            self._client.connect(host=config['MQTT'][self._farm]['host'],
                                 port=config['MQTT'][self._farm]['port'])
        elif self._kind == 'local':
            try:
                self._client.connect(host=f'smappee{self._service_location.device_serial_number}.local',
                                     port=config['MQTT']['local']['port'])
            except socket.gaierror as _:
                # unable to connect to local Smappee device (host unavailable)
                return
            except socket.timeout as _:
                return

        self._client.loop_start()

    def stop(self):
        self._client.loop_stop()


class SmappeeLocalMqtt(threading.Thread):
    """Smappee local MQTT wrapper."""

    def __init__(self, serial_number=None):
        self._client = None
        self.service_location = None
        self._serial_number = serial_number
        self._service_location_id = None
        self._service_location_uuid = None
        threading.Thread.__init__(
            self,
            name=f'SmappeeLocalMqttListener_{self._serial_number}'
        )

        self.realtime = {}
        self.phase_type = None
        self.measurements = {}

        self.switch_sensors = []
        self.smart_plugs = []
        self.actuators_connection_state = {}
        self.actuators_state = {}

        self._timezone = None

    @property
    def topic_prefix(self):
        return f'servicelocation/{self._service_location_uuid}'

    def _on_connect(self, client, userdata, flags, rc):
        self._client.subscribe(topic='#')

    def _on_disconnect(self, client, userdata, rc):
        pass

    def _get_client_id(self):
        return f"smappeeLocalMQTT-{self._serial_number}"

    def _on_message(self, client, userdata, message):
        try:
            # realtime local power values
            if message.topic.endswith('/realtime'):
                self.realtime = json.loads(message.payload)
                if self.service_location is not None:
                    self.service_location._update_realtime_data(realtime_data=self.realtime)

            elif message.topic.endswith('/config'):
                c = json.loads(message.payload)
                self._timezone = c.get('timeZone')
                self._service_location_id = c.get('serviceLocationId')
                self._service_location_uuid = c.get('serviceLocationUuid')
                self._serial_number = c.get('serialNumber')
            elif message.topic.endswith('channelConfig'):
                pass
            elif message.topic.endswith('/channelConfigV2'):
                self._channel_config = json.loads(message.payload)
                self.phase_type = self._channel_config.get('dataProcessingSpecification', {}).get('phaseType', None)

                # extract measurements from channelConfigV2
                measurements_dict = {}
                for m in self._channel_config.get('dataProcessingSpecification', {}).get('measurements', []):
                    if m.get('flow') == 'CONSUMPTION' and m.get('connectionType') == 'SUBMETER':
                        if not m['name'] in measurements_dict.keys():
                            measurements_dict[m['name']] = []
                        measurements_dict[m['name']].append(m['publishIndex'])
                    elif m.get('flow') == 'CONSUMPTION' and m.get('connectionType') == 'GRID':
                        if not 'Grid' in measurements_dict.keys():
                            measurements_dict['Grid'] = []
                        measurements_dict['Grid'].append(m['publishIndex'])
                    elif m.get('flow') == 'PRODUCTION' and m.get('connectionType') == 'GRID':
                        if not 'Solar' in measurements_dict.keys():
                            measurements_dict['Solar'] = []
                        measurements_dict['Solar'].append(m['publishIndex'])

                self.measurements = {}
                for m_name, m_index in measurements_dict.items():
                    self.measurements[m_name] = list(set(m_index))

            elif message.topic.endswith('/sensorConfig'):
                pass
            elif message.topic.endswith('/homeControlConfig'):
                # switches
                switches = json.loads(message.payload).get('switchActuators', [])
                for switch in switches:
                    if switch['serialNumber'].startswith('4006'):
                        self.switch_sensors.append({
                            'nodeId': switch['nodeId'],
                            'name': switch['name'],
                            'serialNumber': switch['serialNumber']
                        })

                # plugs
                plugs = json.loads(message.payload).get('smartplugActuators', [])
                for plug in plugs:
                    self.smart_plugs.append({
                        'nodeId': plug['nodeId'],
                        'name': plug['name']
                    })
            elif message.topic.endswith('/presence'):
                pass
            elif message.topic.endswith('/aggregated'):
                pass
            elif message.topic.endswith('/aggregatedGW'):
                pass
            elif message.topic.endswith('/aggregatedSwitch'):
                pass
            elif message.topic.endswith('/etc/measuredvalues'):
                pass
            elif message.topic.endswith('/networkstatistics'):
                pass
            elif message.topic.endswith('/scheduler'):
                pass
            elif message.topic.endswith('/devices'):
                pass
            elif message.topic.endswith('/action/setcurrent'):
                pass
            elif message.topic.endswith('/trigger'):
                pass
            elif message.topic.endswith('/connectionState'):
                actuator_id = int(message.topic.split('/')[-2])
                self.actuators_connection_state[actuator_id] = json.loads(message.payload).get('value')
            elif message.topic.endswith('/state'):
                actuator_id = int(message.topic.split('/')[-2])
                self.actuators_state[actuator_id] = json.loads(message.payload).get('value')

                if self.service_location is not None:
                    self.service_location.set_actuator_state(
                        id=actuator_id,
                        state='{0}_{0}'.format(self.actuators_state[actuator_id]),
                        api=False
                    )
            elif message.topic.endswith('/setstate'):
                actuator_id = int(message.topic.split('/')[-2])
                p = str(message.payload.decode('utf-8')).replace("\'", "\"")
                self.actuators_state[actuator_id] = json.loads(p).get('value')
            elif config['MQTT']['discovery']:
                print('Processing MQTT message from topic {0} with value {1}'.format(message.topic, message.payload))

        except Exception:
            traceback.print_exc()

    def set_actuator_state(self, service_location_id, actuator_id, state_id):
        state = None
        if state_id == 'ON_ON':
            state = 'ON'
        elif state_id == 'OFF_OFF':
            state = 'OFF'

        if state is not None:
            self._client.publish(
                topic="servicelocation/{0}/plug/{1}/setstate".format(self._service_location_uuid, actuator_id),
                payload=json.dumps({"value": state})
            )

    def is_config_ready(self, timeout=60, interval=5):
        c = 0
        while c < timeout:
            if self.phase_type is not None and self._serial_number is not None:
                return self._serial_number
            c += interval
            time.sleep(interval)

    def start_and_wait_for_config(self):
        self.start()
        return self.is_config_ready()

    def start_attempt(self):
        client = mqtt.Client(client_id='smappeeLocalMqttConnectionAttempt')
        try:
            client.connect(host=f'smappee{self._serial_number}.local', port=config['MQTT']['local']['port'])
        except Exception:
            return False

        return True

    def start(self):
        self._client = mqtt.Client(client_id=self._get_client_id())
        self._client.on_connect = lambda client, userdata, flags, rc: self._on_connect(client, userdata, flags, rc)
        self._client.on_message = lambda client, userdata, message: self._on_message(client, userdata, message)
        self._client.on_disconnect = lambda client, userdata, rc: self._on_disconnect(client, userdata, rc)

        #  self._client.tls_set(None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1)
        try:
            self._client.connect(host=f'smappee{self._serial_number}.local', port=config['MQTT']['local']['port'])
        except socket.gaierror as _:
            # unable to connect to local Smappee device (host unavailable)
            return
        except socket.timeout as _:
            return

        self._client.loop_start()

    def stop(self):
        self._client.loop_stop()
