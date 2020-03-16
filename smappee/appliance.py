class SmappeeAppliance:

    def __init__(self, id, name, type):
        self.id = id
        self.name = name
        self.type = type
        self.state = False
        self.power = None

    def set_state(self, state):
        self.state = state

    def set_power(self, power):
        self.power = power

