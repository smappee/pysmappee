class SmappeeActuator:

    def __init__(self, id, name, serialnumber, state_values, connection_state, type):
        # configuration details
        self._id = id
        self._name = name
        self._serialnumber = serialnumber
        self._state_values = state_values
        self._type = type

        # states
        self._connection_state = connection_state
        self._state = None

        # extract current state and possible values from state_values
        self._state_options = []
        for s in self._state_values:
            self._state_options.append(s.get('id'))
            if s.get('current'):
                self._state = s.get('id')

        # aggregated values (only for Smappee Switch)
        self._consumption_today = None

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def serialnumber(self):
        return self._serialnumber

    @serialnumber.setter
    def serialnumber(self, serialnumber):
        self._serialnumber = serialnumber

    @property
    def state_values(self):
        return self._state_values

    @property
    def type(self):
        return self._type

    @property
    def connection_state(self):
        return self._connection_state

    @connection_state.setter
    def connection_state(self, connection_state):
        self._connection_state = connection_state

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        if state in ['ON', 'OFF']:  # backwards compatibility (retained MQTT)
            state = f'{state}_{state}'

        self._state = state

    @property
    def state_options(self):
        return self._state_options

    @property
    def consumption_today(self):
        return self._consumption_today

    @consumption_today.setter
    def consumption_today(self, consumption_today):
        self._consumption_today = consumption_today

