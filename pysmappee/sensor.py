class SmappeeSensor:

    def __init__(self, id, name, channels):
        # configuration details
        self._id = id
        self._name = name

        # list of dicts with keys name, ppu, uom, enabled, type (water/gas), channel (id)
        self._channels = channels
        for c in self.channels:
            c['value_today'] = 0  # aggregated value

        # states
        self._temperature = None
        self._humidity = None
        self._battery = None

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def channels(self):
        return self._channels

    def update_today_values(self, record):
        for channel in self._channels:
            channel['value_today'] = record[f"value{channel.get('channel')}"] / channel.get('ppu')

    @property
    def temperature(self):
        return self._temperature

    @temperature.setter
    def temperature(self, temperature):
        self._temperature = temperature

    @property
    def humidity(self):
        return self._humidity

    @humidity.setter
    def humidity(self, humidity):
        self._humidity = humidity

    @property
    def battery(self):
        return self._battery

    @battery.setter
    def battery(self, battery):
        self._battery = battery
