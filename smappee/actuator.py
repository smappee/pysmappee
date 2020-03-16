class SmappeeActuator:

    def __init__(self, id, name, actuator_type):
        # configuration details
        self.id = id
        self.name = name
        self.actuator_type = actuator_type
        self.serialnumber = None

        # states (only for Smappee Switch)
        self.state = None
        self.connection_state = None

        # aggregated values (only for Smappee Switch)
        self.consumption_today = None

    def set_state(self, state):
        self.state = state

    def set_connection_state(self, connectionState):
        self.connection_state = connectionState

    def set_serialnumber(self, serialnumber):
        self.serialnumber = serialnumber

    def set_actuator_type(self, actuator_type):
        self.actuator_type = actuator_type

    def set_consumption_today(self, consumption_today):
        self.consumption_today = consumption_today
