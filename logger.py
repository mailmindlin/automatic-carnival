from typing import List, Dict, NewType, Optional
from ir import Node

ExId = NewType('ExId', int)


class LogEvent(object):
    """Base log event type."""
    def __init__(self, exId: ExId, cycle: int):
        self.exId = exId
        self.cycle = cycle


class InstructionFetchEvent(LogEvent):
    """Event generated when instruction enters IF"""
    def __init__(self, exId: ExId, cycle: int, node: Node):
        super().__init__(exId, cycle)
        self.node = node


class StageAdvanceEvent(LogEvent):
    """Event generated when instruction enters ID/"""
    def __init__(self, exId: ExId, cycle: int, stage: str):
        super().__init__(exId, cycle)
        self.stage = stage


class PipelineStallEvent(LogEvent):
    def __init__(self, exId: ExId, cycle: int, stalls: int):
        super().__init__(exId, cycle)


class PipelineExitEvent(LogEvent):
    def __init__(self, exId: ExId, cycle: int):
        super().__init__(exId, cycle)


class EndOfCycleEvent(LogEvent):
    def __init__(self, cycle):
        super().__init__(-1, cycle)


class LogEntry(object):
    _strcache: Optional[str]

    def __init__(self, exId: ExId, node: Node, startCycle: int, width: int):
        self.exId = exId
        self.node = node
        self.startCycle = startCycle
        self.width = width
        self.slots = []
    
    def markCycle(self, cycle: int, name: str):
        offset = cycle - self.startCycle
        if len(self.slots) <= offset + 1:
            self.slots += [None] * (1 + len(self.slots) - offset)
        self.slots[offset] = name

    def __str__(self) -> str:
        if hasattr(self, '_strcache'):
            return self._strcache
        result = f'{self.node!s:<20}'
        result += '.   ' * self.startCycle
        result += ''.join(f"{slot or '.':<4}" for slot in self.slots)
        result += '.   ' * (self.width - len(self.slots) - self.startCycle)
        return result


class Logger(object):
    def __init__(self, cycles: int):
        self.cycles = cycles
        self.history: List[LogEntry] = []
        self.current: Dict[ExId, LogEntry] = {}
        self.cycleMissed = set()

    def update(self, event: LogEvent) -> None:
        """Apply effects of event."""
        if isinstance(event, InstructionFetchEvent):
            entry = LogEntry(event.exId, event.node, event.cycle, self.cycles)
            entry.markCycle(event.cycle, 'IF')
            self.history.append(entry)
            self.current[event.exId] = entry
        elif isinstance(event, StageAdvanceEvent):
            entry = self.current[event.exId]
            self.cycleMissed.discard(entry)
            entry.markCycle(event.cycle, event.stage)
        elif isinstance(event, PipelineStallEvent):
            entry = self.current[event.exId]
            self.cycleMissed.discard(entry)
            print("PIPELINE STALL")
        elif isinstance(event, PipelineExitEvent):
            entry = self.current.pop(event.exId)
            self.cycleMissed.discard(entry)
        elif isinstance(event, EndOfCycleEvent):
            # Fill asterisk for stages missed
            for entry in self.cycleMissed:
                if entry.startCycle <= event.cycle - 5:
                    self.current.pop(entry.exId)
                entry.markCycle(event.cycle, '*')
            self.cycleMissed = set(self.current.values())
        else:
            raise ValueError("Unknown event type")
    
    def print(self) -> None:
        print('CPU Cycles ===>     ' + ''.join(f'{i:<4}' for i in range(1, self.cycles + 1)))
        for entry in self.history:
            print(entry)
