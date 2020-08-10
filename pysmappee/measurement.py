"""Support for all kinds of Smappee measurements."""


class SmappeeMeasurement:
    """Representation of a Smappee measurement."""

    def __init__(self, id, name, type, subcircuit_type, channels):
        # configuration details
        self._id = id
        self._name = name
        self._type = type
        self._subcircuit_type = subcircuit_type
        self._channels = channels

        # live states
        self._active_total = None
        self._reactive_total = None
        self._current_total = None

        for c in self.channels:
            c['active'] = None
            c['reactive'] = None
            c['current'] = None

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type

    @property
    def subcircuit_type(self):
        return self._subcircuit_type

    @property
    def channels(self):
        return self._channels

    @property
    def active_total(self):
        return self._active_total

    def update_active(self, active, source='CENTRAL'):
        index = 'powerTopicIndex' if source == 'CENTRAL' else 'consumptionIndex'
        for channel in self.channels:
            if index in channel:
                channel['active'] = active[channel.get(index)]
        self._active_total = sum([c.get('active') for c in self.channels if index in c])

    @property
    def reactive_total(self):
        return self._reactive_total

    def update_reactive(self, reactive, source='CENTRAL'):
        index = 'powerTopicIndex' if source == 'CENTRAL' else 'consumptionIndex'
        for channel in self.channels:
            if index in channel:
                channel['reactive'] = reactive[channel.get(index)]
        self._reactive_total = sum([c.get('reactive') for c in self.channels if index in c])

    @property
    def current_total(self):
        return self._current_total

    def update_current(self, current, source='CENTRAL'):
        index = 'powerTopicIndex' if source == 'CENTRAL' else 'consumptionIndex'
        for channel in self.channels:
            if index in channel:
                channel['current'] = current[channel.get(index)]
        self._current_total = sum([c.get('current') for c in self.channels if index in c])
