from .servicelocation import SmappeeServiceLocation


class Smappee:

    def __init__(self, api, serialnumber=None):
        """
        :param api:
        :param serialNumber:
        """
        # shared api instance
        self.smappee_api = api

        # serialnumber (LOCAL env only)
        self._serialnumber = serialnumber
        self._local_polling = serialnumber is not None

        # service locations accessible from user
        self._service_locations = {}

    def load_service_locations(self, refresh=False):
        locations = self.smappee_api.get_service_locations()
        for service_location in locations['serviceLocations']:
            if service_location.get('serviceLocationId') in self._service_locations:
                # refresh the configuration
                sl = self.service_locations.get(service_location.get('serviceLocationId'))
                sl.load_configuration(refresh=refresh)
            elif 'deviceSerialNumber' in service_location:
                # Create service location object if the serialnumber is known
                sl = SmappeeServiceLocation(service_location_id=service_location.get('serviceLocationId'),
                                            device_serial_number=service_location.get('deviceSerialNumber'),
                                            smappee_api=self.smappee_api)

                # Add sl object
                self.service_locations[service_location.get('serviceLocationId')] = sl

    def load_local_service_location(self):
        # Create service location object
        sl = SmappeeServiceLocation(device_serial_number=self._serialnumber,
                                    smappee_api=self.smappee_api,
                                    local_polling=self._local_polling)

        # Add sl object
        self.service_locations[sl.service_location_id] = sl

    @property
    def local_polling(self):
        return self._local_polling

    @property
    def service_locations(self):
        return self._service_locations

    def update_trends_and_appliance_states(self):
        for _, sl in self.service_locations.items():
            sl.update_trends_and_appliance_states()
