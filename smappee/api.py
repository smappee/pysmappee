import requests
import datetime as dt
import functools
from .helper import urljoin
import pytz
import numbers


def authenticated(func):
    # Decorator to refresh expired access tokens
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        if self._refresh_token is not None and self._token_expiration_time <= dt.datetime.utcnow():
            self.authenticate(refresh=True)
        return func(*args, **kwargs)
    return wrapper


class SmappeeApi(object):

    # dev API v3 base urls
    token_url = 'https://app1pub.smappee.net/dev/v3/oauth2/token'
    servicelocation_url = 'https://app1pub.smappee.net/dev/v3/servicelocation'

    def __init__(self, username, password, client_id, client_secret):
        self._username = username
        self._password = password
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = None
        self._refresh_token = None
        self._token_expiration_time = None

        self.authenticate()

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self._access_token}"}

    def authenticate(self, refresh=False):
        data = {
            "grant_type": "refresh_token" if refresh else "password",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }

        if refresh:
            data["refresh_token"] = self._refresh_token
        else:
            data["username"] = self._username
            data["password"] = self._password

        r = requests.post(self.token_url, data=data)
        r.raise_for_status()
        j = r.json()
        self._access_token = j['access_token']
        self._refresh_token = j['refresh_token']
        self._set_token_expiration_time(expires_in=j['expires_in'])
        return r

    def _set_token_expiration_time(self, expires_in):
        """
        Saves the token expiration time by adding the 'expires in' parameter to the current datetime (in utc).
        """
        self._token_expiration_time = dt.datetime.utcnow() + dt.timedelta(0, expires_in)  # timedelta(days, seconds)

    @authenticated
    def get_service_locations(self):
        r = requests.get(self.servicelocation_url, headers=self.headers)
        r.raise_for_status()

        return r.json()

    @authenticated
    def get_metering_configuration(self, service_location_id):
        url = urljoin(self.servicelocation_url, service_location_id, "meteringconfiguration")
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()

    @authenticated
    def get_service_location_info(self, service_location_id):
        url = urljoin(self.servicelocation_url, service_location_id, "info")
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
        url = urljoin(self.servicelocation_url, service_location_id, "consumption")
        d = self._get_consumption(url=url, start=start, end=end, aggregation=aggregation)
        for block in d['consumptions']:
            if 'alwaysOn' not in block.keys():
                break
            block.update({'alwaysOn': block.get('alwaysOn') / 12})
        return d

    @authenticated
    def get_sensor_consumption(self, service_location_id, sensor_id, start, end, aggregation):
        url = urljoin(self.servicelocation_url, service_location_id, "sensor", sensor_id, "consumption")
        return self._get_consumption(url=url, start=start, end=end, aggregation=aggregation)

    @authenticated
    def get_switch_consumption(self, service_location_id, switch_id, start, end, aggregation):
        url = urljoin(self.servicelocation_url, service_location_id, "switch", switch_id, "consumption")
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

        url = urljoin(self.servicelocation_url, service_location_id, "events")
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
        url = urljoin(self.servicelocation_url, service_location_id, "actuator", actuator_id, "state")
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.text

    @authenticated
    def set_actuator_state(self, service_location_id, actuator_id, state_id, duration=None):
        url = urljoin(self.servicelocation_url, service_location_id, "actuator", actuator_id, state_id)
        data = {} if duration is None else {"duration": duration}
        r = requests.post(url, headers=self.headers, json=data)
        r.raise_for_status()
        return r

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
