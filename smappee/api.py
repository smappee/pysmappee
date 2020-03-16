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
        if self.refresh_token is not None and \
           self.token_expiration_time <= dt.datetime.utcnow():
            self.re_authenticate()
        return func(*args, **kwargs)
    return wrapper


class SmappeeApi(object):

    # dev API v3 base urls
    token_url = 'https://app1pub.smappee.net/dev/v3/oauth2/token'
    servicelocation_url = 'https://app1pub.smappee.net/dev/v3/servicelocation'

    def __init__(self, username, password, client_id, client_secret):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.refresh_token = None
        self.token_expiration_time = None

        self.authenticate()

    def authenticate(self):
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        r = requests.post(self.token_url, data=data)
        r.raise_for_status()
        j = r.json()
        self.access_token = j['access_token']
        self.refresh_token = j['refresh_token']
        self._set_token_expiration_time(expires_in=j['expires_in'])
        return r

    def _set_token_expiration_time(self, expires_in):
        """
        Saves the token expiration time by adding the 'expires in' parameter to the current datetime (in utc).
        """
        self.token_expiration_time = dt.datetime.utcnow() + dt.timedelta(0, expires_in)  # timedelta(days, seconds)

    def re_authenticate(self):
        """
        Uses the refresh token to request a new access token, refresh token and expiration date.
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        r = requests.post(self.token_url, data=data)
        r.raise_for_status()
        j = r.json()
        self.access_token = j['access_token']
        self.refresh_token = j['refresh_token']
        self._set_token_expiration_time(expires_in=j['expires_in'])
        return r

    @authenticated
    def get_service_locations(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        r = requests.get(self.servicelocation_url, headers=headers)
        r.raise_for_status()

        return r.json()

    @authenticated
    def get_metering_configuration(self, service_location_id):
        url = urljoin(self.servicelocation_url, service_location_id, "meteringconfiguration")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.json()

    @authenticated
    def get_service_location_info(self, service_location_id):
        url = urljoin(self.servicelocation_url, service_location_id, "info")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        r = requests.get(url, headers=headers)
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
            block.update({'alwaysOn': block['alwaysOn'] / 12})
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

        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {
            "aggregation": aggregation,
            "from": start,
            "to": end
        }
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r.json()

    @authenticated
    def get_events(self, service_location_id, appliance_id, start, end, max_number=None):
        start, end = self._to_milliseconds(start), self._to_milliseconds(end)

        url = urljoin(self.servicelocation_url, service_location_id, "events")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {
            "from": start,
            "to": end,
            "applianceId": appliance_id,
            "maxNumber": max_number
        }
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r.json()

    @authenticated
    def get_actuator_state(self, service_location_id, actuator_id):
        url = urljoin(self.servicelocation_url, service_location_id, "actuator", actuator_id, "state")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.text

    @authenticated
    def actuator_on(self, service_location_id, actuator_id, duration=None):
        return self._actuator_on_off(
            on_off='on', service_location_id=service_location_id,
            actuator_id=actuator_id, duration=duration)

    @authenticated
    def actuator_off(self, service_location_id, actuator_id, duration=None):
        return self._actuator_on_off(
            on_off='off', service_location_id=service_location_id,
            actuator_id=actuator_id, duration=duration)

    def _actuator_on_off(self, on_off, service_location_id, actuator_id, duration=None):
        url = urljoin(self.servicelocation_url, service_location_id, "actuator", actuator_id, on_off)
        headers = {"Authorization": f"Bearer {self.access_token}"}
        data = {} if duration is None else {"duration": duration}
        r = requests.post(url, headers=headers, json=data)
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
