import requests
import datetime as dt
import functools
from .config import config
from .helper import urljoin
from oauthlib.oauth2 import TokenExpiredError
from requests import Response
from requests_oauthlib import OAuth2Session
import pytz
import numbers


def authenticated(func):
    # Decorator to refresh expired access tokens
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        try:
            return func(*args, **kwargs)
        except TokenExpiredError:
            self._oauth.token = self.refresh_tokens()
            return func(*args, **kwargs)
    return wrapper


class SmappeeApi(object):

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
    def headers(self):
        return {"Authorization": f"Bearer {self._oauth.access_token}"}

    @authenticated
    def get_service_locations(self):
        r = requests.get(config['API_URL'][self._farm]['servicelocation_url'], headers=self.headers)
        r.raise_for_status()

        return r.json()

    @authenticated
    def get_metering_configuration(self, service_location_id):
        url = urljoin(config['API_URL'][self._farm]['servicelocation_url'], service_location_id, "meteringconfiguration")
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.json()

    @authenticated
    def get_service_location_info(self, service_location_id):
        url = urljoin(config['API_URL'][self._farm]['servicelocation_url'], service_location_id, "info")
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
        url = urljoin(config['API_URL'][self._farm]['servicelocation_url'], service_location_id, "consumption")
        d = self._get_consumption(url=url, start=start, end=end, aggregation=aggregation)
        for block in d['consumptions']:
            if 'alwaysOn' not in block.keys():
                break
            block.update({'alwaysOn': block.get('alwaysOn') / 12})
        return d

    @authenticated
    def get_sensor_consumption(self, service_location_id, sensor_id, start, end, aggregation):
        url = urljoin(config['API_URL'][self._farm]['servicelocation_url'], service_location_id, "sensor", sensor_id, "consumption")
        return self._get_consumption(url=url, start=start, end=end, aggregation=aggregation)

    @authenticated
    def get_switch_consumption(self, service_location_id, switch_id, start, end, aggregation):
        url = urljoin(config['API_URL'][self._farm]['servicelocation_url'], service_location_id, "switch", switch_id, "consumption")
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

        url = urljoin(config['API_URL'][self._farm]['servicelocation_url'], service_location_id, "events")
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
        url = urljoin(config['API_URL'][self._farm]['servicelocation_url'], service_location_id, "actuator", actuator_id, "state")
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.text

    @authenticated
    def set_actuator_state(self, service_location_id, actuator_id, state_id, duration=None):
        url = urljoin(config['API_URL'][self._farm]['servicelocation_url'], service_location_id, "actuator", actuator_id, state_id)
        data = {} if duration is None else {"duration": duration}
        r = requests.post(url, headers=self.headers, json=data)
        r.raise_for_status()
        return r

    @authenticated
    def get_actuator_connection_state(self, service_location_id, actuator_id):
        url = urljoin(config['API_URL'][self._farm]['servicelocation_url'], service_location_id, "actuator", actuator_id, "connectionstate")
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
