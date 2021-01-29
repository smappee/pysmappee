"""Support for cloud and local Smappee API."""
import datetime as dt
import functools
import numbers
import pytz
import requests
from cachetools import TTLCache
from requests.exceptions import HTTPError, ConnectTimeout, ReadTimeout, \
    ConnectionError as RequestsConnectionError
from requests_oauthlib import OAuth2Session
from .config import config
from .helper import urljoin


def authenticated(func):
    # Decorator to refresh expired access tokens
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            if e.response.status_code == 401:
                self._oauth.token = self.refresh_tokens()
            return func(*args, **kwargs)
    return wrapper


class SmappeeApi:
    """Public Smappee cloud API wrapper."""

    def __init__(
            self,
            client_id,
            client_secret,
            redirect_uri=None,
            token=None,
            token_updater=None,
            farm=1
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_updater = token_updater
        self._farm = farm

        extra = {"client_id": self._client_id, "client_secret": self._client_secret}

        self._oauth = OAuth2Session(
            client_id=client_id,
            token=token,
            redirect_uri=redirect_uri,
            auto_refresh_kwargs=extra,
            token_updater=token_updater,
        )

    @property
    def farm(self):
        return self._farm

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self._oauth.access_token}"}

    @authenticated
    def get_service_locations(self):
        r = requests.get(config['API_URL'][self._farm]['servicelocation_url'], headers=self.headers)
        r.raise_for_status()

        return r.json()

    @authenticated
    def get_metering_configuration(self, service_location_id):
        url = urljoin(
            config['API_URL'][self._farm]['servicelocation_url'],
            service_location_id,
            "meteringconfiguration"
        )
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()

    @authenticated
    def get_service_location_info(self, service_location_id):
        url = urljoin(
            config['API_URL'][self._farm]['servicelocation_url'],
            service_location_id,
            "info"
        )
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()

    @authenticated
    def get_consumption(self, service_location_id, start, end, aggregation):
        """
        aggregation : int
            1 = 5 min values (only available for the last 14 days)
            2 = hourly values
            3 = daily values
            4 = monthly values
            5 = quarterly values
            6 = ...
            7 = ...
            8 = ...
        """
        url = urljoin(
            config['API_URL'][self._farm]['servicelocation_url'],
            service_location_id,
            "consumption"
        )
        d = self._get_consumption(url=url, start=start, end=end, aggregation=aggregation)
        for block in d['consumptions']:
            if 'alwaysOn' not in block.keys():
                break
            block.update({'alwaysOn': block.get('alwaysOn') / 12})
        return d

    @authenticated
    def get_sensor_consumption(self, service_location_id, sensor_id, start, end, aggregation):
        url = urljoin(
            config['API_URL'][self._farm]['servicelocation_url'],
            service_location_id,
            "sensor",
            sensor_id,
            "consumption"
        )
        return self._get_consumption(url=url, start=start, end=end, aggregation=aggregation)

    @authenticated
    def get_switch_consumption(self, service_location_id, switch_id, start, end, aggregation):
        url = urljoin(
            config['API_URL'][self._farm]['servicelocation_url'],
            service_location_id,
            "switch",
            switch_id,
            "consumption"
        )
        return self._get_consumption(url=url, start=start, end=end, aggregation=aggregation)

    def _get_consumption(self, url, start, end, aggregation):
        start, end = self._to_milliseconds(start), self._to_milliseconds(end)

        params = {
            "aggregation": aggregation,
            "from": start,
            "to": end
        }
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        return r.json()

    @authenticated
    def get_events(self, service_location_id, appliance_id, start, end, max_number=None):
        start, end = self._to_milliseconds(start), self._to_milliseconds(end)

        url = urljoin(
            config['API_URL'][self._farm]['servicelocation_url'],
            service_location_id,
            "events"
        )
        params = {
            "from": start,
            "to": end,
            "applianceId": appliance_id,
            "maxNumber": max_number
        }
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        return r.json()

    @authenticated
    def get_actuator_state(self, service_location_id, actuator_id):
        url = urljoin(
            config['API_URL'][self._farm]['servicelocation_url'],
            service_location_id,
            "actuator",
            actuator_id,
            "state"
        )
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.text

    @authenticated
    def set_actuator_state(self, service_location_id, actuator_id, state_id, duration=None):
        url = urljoin(
            config['API_URL'][self._farm]['servicelocation_url'],
            service_location_id,
            "actuator",
            actuator_id,
            state_id
        )
        data = {} if duration is None else {"duration": duration}
        r = requests.post(url, headers=self.headers, json=data)
        r.raise_for_status()
        return r

    @authenticated
    def get_actuator_connection_state(self, service_location_id, actuator_id):
        url = urljoin(
            config['API_URL'][self._farm]['servicelocation_url'],
            service_location_id,
            "actuator",
            actuator_id,
            "connectionstate"
        )
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.text

    def _to_milliseconds(self, time):
        if isinstance(time, dt.datetime):
            if time.tzinfo is None:
                time = time.replace(tzinfo=pytz.UTC)
            return int(time.timestamp() * 1e3)
        elif isinstance(time, numbers.Number):
            return time
        else:
            raise NotImplementedError("Time format not supported. Use milliseconds since epoch,\
                                        Datetime or Pandas Datetime")

    def get_authorization_url(self, state):
        return self._oauth.authorization_url(config['API_URL'][self._farm]['authorize_url'], state)

    def request_token(self, authorization_response, code):
        return self._oauth.fetch_token(
            token_url=config['API_URL'][self._farm]['token_url'],
            authorization_response=authorization_response,
            code=code,
            client_secret=self.client_secret,
        )

    def refresh_tokens(self):
        token = self._oauth.refresh_token(token_url=config['API_URL'][self._farm]['token_url'])

        if self.token_updater is not None:
            self.token_updater(token)

        return token


class SmappeeLocalApi:
    """Smappee local API wrapper."""

    def __init__(
            self,
            ip
    ):
        self._ip = ip
        self.session = requests.Session()

        # default indices for Smappee Energy and Solar
        self.consumption_indices = ['phase0ActivePower', 'phase1ActivePower', 'phase2ActivePower']
        self.production_indices = ['phase3ActivePower', 'phase4ActivePower', 'phase5ActivePower']

        # cache instantaneous load
        self.load_cache = TTLCache(maxsize=2, ttl=5)

    @property
    def host(self):
        return f'http://{self._ip}/gateway/apipublic'

    @property
    def headers(self):
        return {"Content-Type": "application/json"}

    def _post(self, url, data=None, retry=False):
        try:
            _url = urljoin(self.host, url)
            r = self.session.post(_url,
                                  data=data,
                                  headers=self.headers,
                                  timeout=2)
            r.raise_for_status()

            msg = r.json()
            if not retry and 'error' in msg \
                    and msg['error'] == 'Error not authenticated. Use Logon first!':
                self.logon()
                return self._post(url=url, data=data, retry=True)

            return msg
        except (ConnectTimeout, ReadTimeout, RequestsConnectionError, HTTPError):
            return None

    def logon(self):
        return self._post(url='logon', data='admin')

    def load_advanced_config(self):
        return self._post(url='advancedConfigPublic', data='load')

    def load_channels_config(self):
        # Method only available on Smappee2-series devices

        # reset consumption and production indices
        self.consumption_indices, self.production_indices = [], []

        cc = self._post(url='channelsConfigPublic', data='load')
        for input_channel in cc['inputChannels']:
            if input_channel['inputChannelConnection'] == 'GRID':
                if input_channel['inputChannelType'] == 'CONSUMPTION':
                    self.consumption_indices.append(f'phase{input_channel["ctInput"]}ActivePower')
                elif input_channel['inputChannelType'] == 'PRODUCTION':
                    self.production_indices.append(f'phase{input_channel["ctInput"]}ActivePower')

        return cc

    def load_config(self):
        c = self._post(url='configPublic', data='load')

        # get emeterConfiguration to decide cons and prod indices for solar series (11)
        emeterConfiguration = None
        for conf in c:
            if 'key' in conf and conf['key'] == 'emeterConfiguration' and 'value' in conf:
                emeterConfiguration = conf['value']

        # three phase grid and solar
        if emeterConfiguration == "11":
            pass  # use default ones
        # single phase grid and solar
        elif emeterConfiguration == "17":
            self.consumption_indices = ['phase0ActivePower']
            self.production_indices = ['phase1ActivePower']
        # three phase grid, no solar
        elif emeterConfiguration == "4":
            self.production_indices = []
        # single phase grid, no solar
        elif emeterConfiguration == "0":
            self.consumption_indices = ['phase0ActivePower']
            self.production_indices = []
        # dual phase grid and solar
        elif emeterConfiguration == "16":
            self.consumption_indices = ['phase0ActivePower', 'phase1ActivePower']
            self.production_indices = ['phase2ActivePower', 'phase3ActivePower']

        return c

    def load_command_control_config(self):
        return self._post(url='commandControlPublic', data='load')

    def load_instantaneous(self):
        return self._post(url='instantaneous', data='loadInstantaneous')

    def active_power(self, solar=False):
        """
        Get the current active power consumption or solar production. Result is cached.

        :param solar:
        :return:
        """
        if solar and 'instantaneous_solar' in self.load_cache:
            return self.load_cache['instantaneous_solar']
        elif not solar and 'instantaneous_load' in self.load_cache:
            return self.load_cache['instantaneous_load']

        inst = self.load_instantaneous()

        if inst is None:
            return None

        power_keys = self.production_indices if solar else self.consumption_indices

        values = [float(i['value']) for i in inst if i['key'] in power_keys]
        if values:
            power = int(sum(values) / 1000)
        else:
            power = 0

        if solar:
            self.load_cache['instantaneous_solar'] = power
        else:
            self.load_cache['instantaneous_load'] = power

        return power

    def set_actuator_state(self, service_location_id, actuator_id, state_id, duration=None):
        if state_id == 'ON_ON':
            return self.on_command_control(val_id=actuator_id)
        elif state_id == 'OFF_OFF':
            return self.off_command_control(val_id=actuator_id)

    def on_command_control(self, val_id):
        data = "control,{\"controllableNodeId\":\"" + str(val_id) + "\",\"action\":\"ON\"}"
        return self._post(url='commandControlPublic', data=data)

    def off_command_control(self, val_id):
        data = "control,{\"controllableNodeId\":\"" + str(val_id) + "\",\"action\":\"OFF\"}"
        return self._post(url='commandControlPublic', data=data)
