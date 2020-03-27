class SmappeeAppliance:

    def __init__(self, id, name, type, source_type):
        self._id = id
        self._name = name
        self._type = type
        self._source_type = source_type
        self._state = False
        self._power = None

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
    def source_type(self):
        return self._source_type

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state

    @property
    def power(self):
        return self._power

    @power.setter
    def power(self, power):
        self._power = power

