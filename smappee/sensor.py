class SmappeeSensor:

    def __init__(self, id, name, channels):
        # configuration details
        self.id = id
        self.name = name

        # list of dicts with keys name, ppu, uom, enabled, type (water/gas), channel (id)
        self.channels = channels
        for c in self.channels:
            c['value_today'] = 0  # aggregated value

        # states
        self.temperature = None
        self.humidity = None
        self.battery = None

    def update_today_values(self, record):
        for channel in self.channels:
            channel['value_today'] = record[f"value{channel['channel']}"] / channel['ppu']

    def get_channels(self):
        return self.channels

    def set_temperature(self, temperature):
        self.temperature = temperature

    def set_humidity(self, humidity):
        self.humidity = humidity

    def set_battery(self, battery):
        self.battery = battery

