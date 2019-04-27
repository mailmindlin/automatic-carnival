"""Helps with recording CPU events."""
from typing import List, Set, Dict, NewType, Optional
from ir import Node, MIPSInstruction

ExId = NewType('ExId', int)

PRINT_EVENTS = False


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
    
    def __repr__(self):
        return f'InstructionFetchEvent(exId={self.exId!r}, cycle={self.cycle!r}, node={self.node!r})'


class StageAdvanceEvent(LogEvent):
    """Event generated when instruction enters a ID/EX/MEM/WB."""

    def __init__(self, exId: ExId, cycle: int, stage: str):
        super().__init__(exId, cycle)
        self.stage = stage
    
    def __repr__(self):
        return f'StageAdvanceEvent(exId={self.exId!r}, cycle={self.cycle!r}, stage={self.stage!r})'


class PipelineStallEvent(LogEvent):
    """
    Event generated when the pipeline stalls.

    This event may cause nop instructions to be generated.
    """

    def __init__(self, exId: ExId, cycle: int, stage: str, stalls: int):
        super().__init__(exId, cycle)
        self.stage = stage
        self.stalls = stalls
    
    def __repr__(self):
        return f'PipelineStallEvent(exId={self.exId}, cycle={self.cycle}, stage={self.stage!r}, stalls={self.stalls!r})'


class PipelineExitEvent(LogEvent):
    """For when an execution unit leaves the pipeline."""

    def __init__(self, exId: ExId, cycle: int):
        super().__init__(exId, cycle)


class EndOfCycleEvent(LogEvent):
    """For when the cycle has been finished."""

    def __init__(self, cycle: int):
        super().__init__(None, cycle)


class LogEntry(object):
    """
    An entry representing a single execution unit.

    An execution unit (tracked by a single EXecution ID), is essentially a single time
    an instruction is executed by the processor, throughout all pipeline stages. This
    is necessarily a more restrictive definition than just an instruction, as the same
    instruction may be executed multiple times, assuming for loops and whatnot.

    Fields
    ------
    exId: ExId
        Execution unit id
    node: Node
        Source node
    startCycle: int
        Cycle that the node started executing in
    width: int
        Generated table width (cycle-cells)
    slots: List[str]
        Current recorded events
    _strcache: Optional[str]
        Cache for __str__

    """
    exId: ExId
    node: Node
    startCycle: int
    width: int
    slots: List[str]
    _strcache: Optional[str]

    def __init__(self, exId: ExId, node: Node, startCycle: int, width: int):
        """Create new entry for execution unit."""
        self.exId = exId
        self.node = node
        self.startCycle = startCycle
        self.width = width
        self.slots = []
    
    def markCycle(self, cycle: int, name: str):
        """Mark entry with a label."""
        offset = cycle - self.startCycle
        if len(self.slots) <= offset:
            self.slots += [None] * (1 + len(self.slots) - offset)
        self.slots[offset] = name
    
    def bake(self):
        """Cache __str__ result."""
        self._strcache = str(self)

    def __str__(self) -> str:
        """Stringify entry, producing a table row."""
        if hasattr(self, '_strcache'):
            return self._strcache
        result = f'{self.node!s:<20}'
        result += '.   ' * self.startCycle
        result += ''.join(f"{slot or '.':<4}" for slot in self.slots)
        result += '.   ' * (self.width - len(self.slots) - self.startCycle)
        return result.rstrip()


class Logger(object):
    """
    Records events from CPU in a human-readable form.

    Fields
    ------
    cycles: int
        Number of cycles wide to print
    history: List[LogEntry]
        History of execution units
    current: Dict[ExId, LogEntry]
        Fast lookup for currently-being-modified entries
    cycleMissed: Set[LogEntry]
        Set of entries not modified the current cycle
    fakeExId: ExId
        Counter for nop inserts
    
    """

    cycles: int
    history: List[LogEntry]
    current: Dict[ExId, LogEntry]
    cycleMissed: Set[LogEntry]
    fakeExId: ExId

    def __init__(self, cycles: int):
        """Create logger of width."""
        self.cycles = cycles
        self.history: List[LogEntry] = []
        self.current: Dict[ExId, LogEntry] = {}
        self.cycleMissed = set()
        self.fakeExId = -1
    
    def lookupIndex(self, entry: LogEntry) -> int:
        """
        Lookup index of `entry` in history.

        Note that history may be modified (e.g., nop's are inserted).
        """
        return len(self.history) - self.history[::-1].index(entry) - 1
    
    def insertNop(self, entry: LogEntry, count: int):
        """Insert `count` nop instructions immediately before `entry`."""
        index = self.lookupIndex(entry)
        node = Node(text='nop', inst=MIPSInstruction.NOP, rs=None)
        nop_entry = LogEntry(self.fakeExId, node, entry.startCycle, self.cycles)
        self.fakeExId -= 1
        nop_entry.markCycle(entry.startCycle, "IF")
        nop_entry.markCycle(entry.startCycle + 1, "ID")
        for _ in range(count):
            self.history.insert(index, nop_entry)
        self.current[nop_entry.exId] = nop_entry
        self.cycleMissed.add(nop_entry)

    def update(self, event: LogEvent) -> None:
        """Apply effects of event."""
        if isinstance(event, InstructionFetchEvent):
            entry = LogEntry(event.exId, event.node, event.cycle, self.cycles)
            if PRINT_EVENTS:
                print(f'Instruction fetch {event.exId}')
            entry.markCycle(event.cycle, 'IF')
            self.history.append(entry)
            self.current[event.exId] = entry
        elif isinstance(event, StageAdvanceEvent):
            if PRINT_EVENTS:
                print(f'Stage advance {event.exId} to {event.stage}')
            entry = self.current[event.exId]
            self.cycleMissed.discard(entry)
            entry.markCycle(event.cycle, event.stage)
        elif isinstance(event, PipelineStallEvent):
            entry: LogEntry = self.current[event.exId]
            if PRINT_EVENTS:
                print(f'Pipeline stall {event.exId} ({entry.node}) with stage {event.stage}')
            self.cycleMissed.discard(entry)
            entry.markCycle(event.cycle, event.stage)
            if event.stalls > 0:
                self.insertNop(entry, event.stalls)
        elif isinstance(event, PipelineExitEvent):
            if PRINT_EVENTS:
                print(f'Remove {event.exId} from pipeline')
            entry: LogEntry = self.current.pop(event.exId)
            self.cycleMissed.discard(entry)
            entry.bake()
        elif isinstance(event, EndOfCycleEvent):
            # Fill asterisk for stages missed
            if PRINT_EVENTS:
                print(f'End of cycle {event.cycle}')
            entry: LogEntry
            for entry in self.cycleMissed:
                entry.markCycle(event.cycle, '*')
                if entry.startCycle <= event.cycle - 4:
                    #print(f'Bake {entry.exId}')
                    self.current.pop(entry.exId)
                    entry.bake()
                if PRINT_EVENTS:
                    print(f'\tmark entry {entry.exId} on cycle {event.cycle}')
            self.cycleMissed = set(self.current.values())
        else:
            raise ValueError("Unknown event type")
    
    def print(self) -> None:
        """Print pipeline state & history to stdout."""
        print('CPU Cycles ===>     ' + ''.join(f'{i:<4}' for i in range(1, self.cycles + 1)).rstrip())
        for entry in self.history:
            print(entry)
