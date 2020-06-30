from .api import SmappeeApi
from .servicelocation import SmappeeServiceLocation


class Smappee(object):

    def __init__(self, api):
        """
        :param api:
        """

        # shared api instance
        self.smappee_api = api

        # service locations accessible from user
        self._service_locations = {}

    def load_service_locations(self, refresh=False):
        locations = self.smappee_api.get_service_locations()
        for service_location in locations['serviceLocations']:
            if service_location.get('serviceLocationId') in self._service_locations:
                # refresh the configuration
                sl = self.service_locations.get(service_location.get('serviceLocationId'))
                sl.load_configuration(refresh=refresh)
            else:
                # Create service location object
                sl = SmappeeServiceLocation(service_location_id=service_location.get('serviceLocationId'),
                                            device_serial_number=service_location.get('deviceSerialNumber'),
                                            smappee_api=self.smappee_api)

                # Add sl object
                self.service_locations[service_location.get('serviceLocationId')] = sl

    @property
    def service_locations(self):
        return self._service_locations

    def update_trends_and_appliance_states(self):
        for _, sl in self.service_locations.items():
            sl.update_trends_and_appliance_states()

