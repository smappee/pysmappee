class SmappeeSmartDevice:

    def __init__(self, uuid, name, category, implementation, minCurrent, maxCurrent, measurements):
        # configuration details
        self.uuid = uuid
        self.name = name
        self.category = category
        self.implementation = implementation
        self.minCurrent = minCurrent
        self.maxCurrent = maxCurrent
        self.channels = measurements

        # connection status
        self.connection_status = None

        # prepare live data
        self.active_total = None
        self.reactive_total = None
        self.current_total = None
        for c in self.channels:
            c['active_power'] = None
            c['reactive_power'] = None
            c['current'] = None
        self.setCurrents = [None, None, None]

    def set_current(self, phase, current):
        self.setCurrents[phase - 1] = current

    def set_connection_status(self, connection_status):
        self.connection_status = connection_status

    # def update_active(self, active):
    #     active_total = 0
    #     for c in self.channels:
    #         c['active_power'] = active[c['publishIndex']]
    #         active_total += c['active_power']
    #     self.active_total = active_total
    #
    # def update_reactive(self, reactive):
    #     reactive_total = 0
    #     for c in self.channels:
    #         c['reactive_power'] = reactive[c['publishIndex']]
    #         reactive_total += c['reactive_power']
    #     self.reactive_total = reactive_total
    #
    # def update_current(self, current):
    #     current_total = 0
    #     for c in self.channels:
    #         c['current'] = current[c['publishIndex']]
    #         current_total += c['current']
    #     self.current_total = current_total
