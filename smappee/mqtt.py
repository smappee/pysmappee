import paho.mqtt.client as mqtt
import threading
import json
import time
import socket
import traceback
from functools import wraps


mqtt_config = dict({
    'central': {
        'host':  '52.51.163.167',
        'port': 80
    },
    'local': {  # only accessible from same network
        'port': 1883,
    },
})

tracking_interval = 60 * 5
heartbeat_interval = 60 * 1


def tracking(func):
    # Decorator to reactivate trackers
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        if time.time() - self.last_tracking > tracking_interval:
            self.publish_tracking()
        if time.time() - self.last_heartbeat > heartbeat_interval:
            self.publish_heartbeat()
        return func(*args, **kwargs)
    return wrapper


class SmappeeMqtt(threading.Thread):

    def __init__(self, service_location, service_location_id, service_location_uuid, device_serial_number, kind):
        self.client = None
        self.service_location = service_location
        self.service_location_id = service_location_id
        self.service_location_uuid = service_location_uuid
        self.device_serial_number = device_serial_number
        self.kind = kind
        self.last_tracking = 0
        self.last_heartbeat = 0
        threading.Thread.__init__(self, name=f'SmappeeMqttListener_{self.service_location_uuid}')

    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe(topic=f'servicelocation/{self.service_location_uuid}/#')

    def publish_tracking(self):
        # turn OFF current tracking and restore
        self.client.publish(
            topic=f"servicelocation/{self.service_location_uuid}/tracking",
            payload=json.dumps({
                "value": "OFF",
                "clientId": self.get_client_id(),
                "serialNumber": self.device_serial_number,
                "type": "RT_VALUES",
            })
        )
        time.sleep(2)
        self.client.publish(
            topic=f"servicelocation/{self.service_location_uuid}/tracking",
            payload=json.dumps({
                "value": "ON",
                "clientId": self.get_client_id(),
                "serialNumber": self.device_serial_number,
                "type": "RT_VALUES",
            })
        )
        self.last_tracking = time.time()

    def publish_heartbeat(self):
        self.client.publish(
            topic=f"servicelocation/{self.service_location_uuid}/homeassistant/heartbeat",
            payload=json.dumps({
                "serviceLocationId": self.service_location_id,
            })
        )
        self.last_heartbeat = time.time()

    def on_disconnect(self, client, userdata, rc):
        pass

    def get_client_id(self):
        return f"smappeeMQTT-python-api-{self.service_location_uuid}-{self.kind}-{int(time.time())}"

    @tracking
    def on_message(self, client, userdata, message):
        try:
            #print('{0} - Processing {1} MQTT message from topic {2} with value {3}'.format(self.service_location_id, self.kind, message.topic, message.payload))
            # realtime central power values
            if message.topic == f'servicelocation/{self.service_location_uuid}/power':
                power_data = json.loads(message.payload)
                self.service_location.update_power_data(power_data=power_data)
            # realtime local power values
            elif message.topic == f'servicelocation/{self.service_location_uuid}/realtime':
                realtime_data = json.loads(message.payload)
                self.service_location.update_realtime_data(realtime_data=realtime_data)
            # powerquality
            elif message.topic == f'servicelocation/{self.service_location_uuid}/powerquality':
                pass

            # tracking and heartbeat
            elif message.topic == f'servicelocation/{self.service_location_uuid}/tracking':
                pass
            elif message.topic == f'servicelocation/{self.service_location_uuid}/homeassistant/heartbeat':
                pass

            # config topics
            elif message.topic == f'servicelocation/{self.service_location_uuid}/config':
                config_details = json.loads(message.payload)
                self.service_location.set_firmware_version(firmware_version=config_details['firmwareVersion'])
            elif message.topic == f'servicelocation/{self.service_location_uuid}/sensorConfig':
                pass
            elif message.topic == f'servicelocation/{self.service_location_uuid}/homeControlConfig':
                pass

            # aggregated consumption values
            elif message.topic == f'servicelocation/{self.service_location_uuid}/aggregated':
                pass

            # presence topic
            elif message.topic == f'servicelocation/{self.service_location_uuid}/presence':
                presence = json.loads(message.payload)
                self.service_location.set_presence(presence=presence['value'])

            # trigger topic
            elif message.topic == f'servicelocation/{self.service_location_uuid}/trigger':
                pass
            elif message.topic == f'servicelocation/{self.service_location_uuid}/trigger/appliance':
                pass
            elif message.topic == f'servicelocation/{self.service_location_uuid}/triggerpush':
                pass
            elif message.topic == f'servicelocation/{self.service_location_uuid}/triggervalue':
                pass

            # harmonic vectors
            elif message.topic == f'servicelocation/{self.service_location_uuid}/h1vector':
                pass

            # controllable nodes (general messages)
            elif message.topic == f'servicelocation/{self.service_location_uuid}':
                pass

            # smart device and ETC topics
            elif message.topic.startswith(f'servicelocation/{self.service_location_uuid}/etc/'):
                if message.topic.endswith('/devices'):
                    devices = json.loads(message.payload)
                    for device in devices:
                        self.service_location.add_smart_device(
                            uuid=device['uuid'],
                            name=device['name'],
                            category=device['category'],
                            implementation=device['implementation'],
                            minCurrent=device['minimumCurrent'],
                            maxCurrent=device['maximumCurrent'],
                            measurements=device['measurements'],
                        )
                elif message.topic.endswith('/action/setcurrent'):
                    smart_device_uuid = message.topic.split('/')[-3]
                    set_current_details = json.loads(message.payload)
                    self.service_location.smart_devices[smart_device_uuid].set_current(phase=set_current_details['phase'],
                                                                                       current=set_current_details['value'])
                elif message.topic.endswith('/state'):
                    details = json.loads(message.payload)
                    smart_device_uuid = details['deviceUUID']
                    connection_status = details['connectionStatus']
                    if smart_device_uuid in self.service_location.smart_devices:
                        self.service_location.smart_devices[smart_device_uuid].set_connection_status(connection_status=connection_status)
                elif message.topic.endswith('/etc/measuredvalues'):
                    pass

                else:
                    print()
                    print(message.topic, message.payload)
                    print()

            # specific HASS.io topics
            elif message.topic == f'servicelocation/{self.service_location_uuid}/homeassistant/event':
                pass
            elif message.topic == f'servicelocation/{self.service_location_uuid}/homeassistant/trigger/etc':
                pass
            elif message.topic.startswith(f'servicelocation/{self.service_location_uuid}/outputmodule/'):
                pass
            elif message.topic == f'servicelocation/{self.service_location_uuid}/scheduler':
                pass

            # actuator topics
            elif message.topic.startswith(f'servicelocation/{self.service_location_uuid}/plug/'):
                plug_id = int(message.topic.split('/')[-2])
                payload = json.loads(message.payload)
                plug_state, plug_state_since = payload['value'], payload['since']

                state_type = message.topic.split('/')[-1]
                if state_type == 'state' and self.kind == 'central':
                    self.service_location.set_actuator_state(id=plug_id,
                                                             state=plug_state,
                                                             since=plug_state_since)
                elif state_type == 'connectionState':
                    self.service_location.set_actuator_connection_state(id=plug_id,
                                                                        connection_state=plug_state,
                                                                        since=plug_state_since)
            else:
                print()
                print(message.topic, message.payload)
                print()
        except Exception as e:
            print('Exception', e)
            traceback.print_exc()

    def start(self):
        self.client = mqtt.Client(client_id=self.get_client_id())
        self.client.username_pw_set(self.service_location_uuid, self.service_location_uuid)
        self.client.on_connect = lambda client, userdata, flags, rc: self.on_connect(client, userdata, flags, rc)
        self.client.on_message = lambda client, userdata, message: self.on_message(client, userdata, message)
        self.client.on_disconnect = lambda client, userdata, rc: self.on_disconnect(client, userdata, rc)

        #  self.client.tls_set(None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1)
        if self.kind == 'central':
            self.client.connect(host=mqtt_config[self.kind]['host'],
                                port=mqtt_config[self.kind]['port'])
        elif self.kind == 'local':
            try:
                self.client.connect(host=f'smappee{self.device_serial_number}.local',
                                    port=mqtt_config['local']['port'])
            except socket.gaierror as _:
                # unable to connect to local Smappee device
                return

        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
