from .api import SmappeeApi
from .servicelocation import SmappeeServiceLocation


class Smappee(object):

    def __init__(self, username, password, client_id, client_secret):
        """
        :param username:
        :param password:
        :param client_id:
        :param client_secret:
        """

        # user credentials
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret

        # shared api instance
        self.smappee_api = SmappeeApi(username=username,
                                      password=password,
                                      client_id=client_id,
                                      client_secret=client_secret)

        # service locations accessible from user
        self.service_locations = {}

    def load_service_locations(self, refresh=False):
        locations = self.smappee_api.get_service_locations()
        for service_location in locations['serviceLocations']:
            if 'deviceSerialNumber' in service_location:
                if service_location['serviceLocationId'] in self.service_locations:
                    # refresh the configuration
                    sl = self.service_locations[service_location['serviceLocationId']]
                    sl.load_configuration(refresh=refresh)
                else:
                    # Create service location object
                    sl = SmappeeServiceLocation(service_location_id=service_location['serviceLocationId'],
                                                service_location_uuid=service_location['serviceLocationUuid'],
                                                name=service_location['name'],
                                                device_serial_number=service_location['deviceSerialNumber'],
                                                smappee_api=self.smappee_api)

                    # Add sl object
                    self.service_locations[service_location['serviceLocationId']] = sl

    def get_service_locations(self):
        return self.service_locations

    def update_consumptions_and_appliance_states(self):
        for _, sl in self.service_locations.items():
            sl.update_trends_and_appliance_states()

