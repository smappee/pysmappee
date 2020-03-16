class SmappeeMeasurement:

    def __init__(self, id, name, type, subcircuitType, channels):
        # configuration details
        self.id = id
        self.name = name
        self.type = type
        self.subcircuitType = subcircuitType
        self.channels = channels

        # live states
        self.active_total = None
        self.reactive_total = None
        self.current_total = None

        for c in self.channels:
            c['active'] = None
            c['reactive'] = None
            c['current'] = None

    def update_active(self, active, source='CENTRAL'):
        for c in self.channels:
            c['active'] = active[c['powerTopicIndex' if source == 'CENTRAL' else 'consumptionIndex']]
        self.active_total = sum([c['active'] for c in self.channels])

    def update_reactive(self, reactive, source='CENTRAL'):
        for c in self.channels:
            c['reactive'] = reactive[c['powerTopicIndex' if source == 'CENTRAL' else 'consumptionIndex']]
        self.reactive_total = sum([c['reactive'] for c in self.channels])

    def update_current(self, current, source='CENTRAL'):
        for c in self.channels:
            c['current'] = current[c['powerTopicIndex' if source == 'CENTRAL' else 'consumptionIndex']]
        self.current_total = sum([c['current'] for c in self.channels])
