from enum import Enum

class TimingEvent(object):
    pass

class CPU(object):
    """
    MIPS CPU emulator

    Fields:
        registers: Map[string, number]
        ...
    """
    def __init__(self, src):
        self.src = src
    
    def updateCycle(self):
        # TODO: impl
        pass
        