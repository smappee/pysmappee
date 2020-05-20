import paho.mqtt.client as mqtt
import threading
import json
import time
import socket
import traceback
from functools import wraps
from .config import config


tracking_interval = 60 * 5
heartbeat_interval = 60 * 1


def tracking(func):
    # Decorator to reactivate trackers
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        if time.time() - self._last_tracking > tracking_interval:
            self._publish_tracking()
        if time.time() - self._last_heartbeat > heartbeat_interval:
            self._publish_heartbeat()
        return func(*args, **kwargs)
    return wrapper


class SmappeeMqtt(threading.Thread):

    def __init__(self, service_location, kind, farm):
        self._client = None
        self._service_location = service_location
        self._kind = kind
        self._farm = farm
        self._last_tracking = 0
        self._last_heartbeat = 0
        threading.Thread.__init__(self, name=f'SmappeeMqttListener_{self._service_location.service_location_uuid}')

    @property
    def topic_prefix(self):
        return f'servicelocation/{self._service_location.service_location_uuid}'

    def _on_connect(self, client, userdata, flags, rc):
        self._client.subscribe(topic=f'{self.topic_prefix}/#')

    def _publish_tracking(self):
        # turn OFF current tracking and restore
        self._client.publish(
            topic=f"{self.topic_prefix}/tracking",
            payload=json.dumps({
                "value": "OFF",
                "clientId": self._get_client_id(),
                "serialNumber": self._service_location.device_serial_number,
                "type": "RT_VALUES",
            })
        )
        time.sleep(2)
        self._client.publish(
            topic=f"{self.topic_prefix}/tracking",
            payload=json.dumps({
                "value": "ON",
                "clientId": self._get_client_id(),
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

    def _get_client_id(self):
        return f"smappeeMQTT-python-api-{self._service_location.service_location_uuid}-{self._kind}-{int(time.time())}"

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
                if message.topic.endswith('/devices'):
                    devices = json.loads(message.payload)
                    for device in devices:
                        self._service_location._add_smart_device(
                            uuid=device.get('uuid'),
                            name=device.get('name'),
                            category=device.get('category'),
                            implementation=device.get('implementation'),
                            minCurrent=device.get('minimumCurrent'),
                            maxCurrent=device.get('maximumCurrent'),
                            measurements=device.get('measurements'),
                        )
                elif message.topic.endswith('/devices/updated'):
                    pass
                elif message.topic.endswith('/action/setcurrent'):
                    smart_device_uuid = message.topic.split('/')[-3]
                    set_current_details = json.loads(message.payload)
                    self._service_location.smart_devices[smart_device_uuid].set_current(
                        phase=set_current_details.get('phase'),
                        current=set_current_details.get('value')
                    )
                elif message.topic.endswith('/action/startcharging'):
                    pass
                elif message.topic.endswith('/action/stopcharging'):
                    pass
                elif message.topic.endswith('/action/smartcharging'):
                    pass
                elif message.topic.endswith('/state'):
                    details = json.loads(message.payload)
                    smart_device_uuid = details.get('deviceUUID')
                    connection_status = details.get('connectionStatus')
                    if smart_device_uuid in self._service_location.smart_devices:
                        self._service_location.smart_devices[smart_device_uuid].set_connection_status(connection_status=connection_status)
                elif message.topic.endswith('/etc/measuredvalues'):
                    pass
                elif message.topic.endswith('/property/chargingstate'):
                    pass

                elif discovery:
                    print(message.topic, message.payload)

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
        except Exception as e:
            traceback.print_exc()

    def start(self):
        self._client = mqtt.Client(client_id=self._get_client_id())
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
                # unable to connect to local Smappee device
                return

        self._client.loop_start()

    def stop(self):
        self._client.loop_stop()
