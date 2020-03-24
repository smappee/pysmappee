class SmappeeActuator:

    def __init__(self, id, name, serialnumber, state_values, type):
        # configuration details
        self.id = id
        self.name = name
        self.serialnumber = serialnumber
        self.state_values = state_values
        self.type = type

        # states (only for Smappee Switch)
        self.connection_state = None
        self.state = None

        # extract current state and possible values from state_values
        self.state_options = []
        for s in self.state_values:
            self.state_options.append(s['id'])
            if s['current']:
                self.state = s['id']

        # aggregated values (only for Smappee Switch)
        self.consumption_today = None

    def set_state(self, state):
        if state in ['ON', 'OFF']:  # backwards compatibility
            state = f'{state}_{state}'

        self.state = state

    def set_connection_state(self, connectionState):
        self.connection_state = connectionState

    def set_serialnumber(self, serialnumber):
        self.serialnumber = serialnumber

    def set_actuator_type(self, actuator_type):
        self.actuator_type = actuator_type

    def set_consumption_today(self, consumption_today):
        self.consumption_today = consumption_today
