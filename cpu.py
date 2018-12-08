from ir import MIPSInstruction, MIPSRegister, Node
from typing import Dict, List, Optional, Tuple, Iterable
from logger import LogEvent, PipelineStallEvent, PipelineExitEvent, StageAdvanceEvent, InstructionFetchEvent, ExId, EndOfCycleEvent


#  dprint = print
dprint = lambda _: None


class PipelineContext(object):
    def __init__(self, exId: ExId, node: Node):
        self.exId = exId
        self.node = node


IFContext = PipelineContext


class IDContext(PipelineContext):
    """
    Fields:
        rdTarget
            Register to write to
    """
    rdTarget: MIPSRegister
    stalled: bool = False

    def __init__(self, source: IFContext, rdTarget: MIPSRegister):
        super().__init__(source.exId, source.node)
        self.rdTarget = rdTarget


class EXContext(PipelineContext):
    """
    Fields:
        rdValue
            Computed output value
        rdTarget
            Register to write to
    """
    rdValue: int
    rdTarget: MIPSRegister

    def __init__(self, source: IDContext, rdValue: int, rdTarget: Optional[MIPSRegister] = None):
        super().__init__(source.exId, source.node)
        self.rdValue = rdValue
        self.rdTarget = rdTarget or source.rdTarget


MEMContext = EXContext


class CPU(object):
    """
    MIPS CPU emulator

    Fields:
        registers: Map[string, number]
        pipeStages: List[Bool]
        pipeline: List[
                       List[Node, List[number]]
                      ]
        instructions: List[Node]
        PC: number
        forwarding: bool
    """
    
    currentCycle: int
    registers: Dict[MIPSRegister, int]
    registerContention: Dict[MIPSRegister, int]
    instructions: List[Node]
    nextExId: ExId

    # Pipeline
    pipeline_id: Optional[IFContext]
    pipeline_ex: Optional[IDContext]
    pipeline_mem: Optional[EXContext]
    pipeline_wb: Optional[MEMContext]

    def __init__(self, src: List[Node], forwarding: bool):
        self.instructions = src
        self.forwarding = forwarding
        self.registers = {}
        self.registerContention = {}
        self.nextExId = 0
        self.currentCycle = 0
        self.pipeline_id = None
        self.pipeline_ex = None
        self.pipeline_mem = None
        self.pipeline_wb = None
    
    @property
    def pc(self) -> int:
        return self.registers.setdefault(MIPSRegister.PC, 0)
    
    @pc.setter
    def pc(self, value: int):
        self.registers[MIPSRegister.PC] = value
    
    @property
    def running(self) -> bool:
        """Get if the CPU is still running."""
        return self.pc < len(self.instructions) \
            or (self.pipeline_id is not None) \
            or (self.pipeline_ex is not None) \
            or (self.pipeline_mem is not None) \
            or (self.pipeline_wb is not None)
    
    def _fetchInstruction(self) -> Iterable[LogEvent]:
        if self.pipeline_id is not None:
            # IF blocked
            return
        
        pc = self.pc
        if pc >= len(self.instructions):
            # End of program
            return
        
        node = self.instructions[pc]
        exId = self.nextExId
        self.nextExId += 1
        self.pc = pc + 1

        # Complete IF
        self.pipeline_id = IFContext(exId, node)
        yield InstructionFetchEvent(exId, self.currentCycle, node)
    
    def _applyID(self) -> Iterable[LogEvent]:
        """Apply the ID stage, and get all generated events."""
        context = self.pipeline_id
        if context is None:
            # ID empty
            dprint("ID empty")
            return
        if self.pipeline_ex is not None:
            # ID blocked
            dprint("ID blocked")
            yield PipelineStallEvent(context.exId, self.currentCycle, 'ID', 0)
            return
        
        node = context.node
        inst = node.inst
        
        rdTarget = MIPSRegister.ZERO
        if inst.isArithmetic or inst.isImmediate:
            # Acquire rd
            rdTarget = node.rd
        elif inst.isBranch:
            rdTarget = MIPSRegister.PC
        
        # Complete ID
        yield StageAdvanceEvent(context.exId, self.currentCycle, "ID")
        self.pipeline_id = None
        self.pipeline_ex = IDContext(context, rdTarget=rdTarget)
    
    def _getExRegister(self, reg: MIPSRegister) -> Tuple[int, int]:
        """
        Get register value & cycle availability.
        This method is only guarunteed to return valid things for calls from the EX stage.

        Parameters
        ----------
        reg
            Register to fetch

        Returns
        --------
        int
            First cycle the register is available
        int
            Register value
        """
        available = self.registerContention.get(reg, 0)
        value = self.registers.get(reg, 0)
        if available <= self.currentCycle:
            return (available, value)
        if self.forwarding:
            if (self.pipeline_mem is not None) and (self.pipeline_mem.rdTarget == reg):
                return (self.currentCycle, self.pipeline_mem.rdValue)
            if (self.pipeline_wb is not None) and (self.pipeline_wb.rdTarget == reg):
                return (self.currentCycle, self.pipeline_wb.rdValue)
        return (available, value)
    
    def _getExInputs(self, node: Node) -> Tuple[int, int, int]:
        """
        Get EX inputs & availability
        Parameters:
        ----------

        Returns:
        int
            First cycle that rs and rt are available
        int
            rs value
        int
            rt value
        """
        inst = node.inst
        if inst == MIPSInstruction.NOP:
            return (0, None, None)
        
        rsAvail, rsValue = self._getExRegister(node.rs)
        if inst.isImmediate:
            return (rsAvail, rsValue, node.immediate)
        
        rtAvail, rtValue = self._getExRegister(node.rt)
        return (max(rsAvail, rtAvail), rsValue, rtValue)
    
    def _acquireRegisterLock(self, reg: MIPSRegister, duration: int):
        if reg in (MIPSRegister.ZERO, MIPSRegister.PC):
            # You can't acquire these
            return
        self.registerContention[reg] = max(self.registerContention.get(reg, 0), self.currentCycle + duration)
    
    def _computeEx(self, inst: MIPSInstruction, rs: int, rt: int) -> int:
        if inst in (MIPSInstruction.ADD, MIPSInstruction.ADDI):
            return rs + rt
        elif inst in (MIPSInstruction.AND, MIPSInstruction.ANDI):
            return rs & rt
        elif inst in (MIPSInstruction.OR, MIPSInstruction.ORI):
            return rs | rt
        elif inst in (MIPSInstruction.SLT, MIPSInstruction.SLTI):
            return 1 if (rs < rt) else 0
        elif inst == MIPSInstruction.BEQ:
            return 1 if (rs == rt) else 0
        elif inst == MIPSInstruction.BNE:
            return 1 if (rs != rt) else 0
        else:
            raise ValueError("Unknown instruction")
    
    def _computeJumpTarget(self, target: str) -> int:
        try:
            return next(i for i, node in enumerate(self.instructions) if node.label == target)
        except StopIteration:
            raise RuntimeError(f'Unable to resolve label target: {target}')
        
    def _applyEX(self) -> Iterable[LogEvent]:
        context = self.pipeline_ex
        if context is None:
            # EX empty
            dprint("EX empty")
            return
        
        node = context.node
        inst = node.inst
        available, rsValue, rtValue = self._getExInputs(context.node)
        now = self.currentCycle if self.forwarding else (self.currentCycle - 1)
        if available > now:
            # ID block
            if not context.stalled:
                yield PipelineStallEvent(context.exId, self.currentCycle, 'ID', available - now)
            else:
                yield PipelineStallEvent(context.exId, self.currentCycle, 'ID', 0)
            context.stalled = True
            return

        if self.pipeline_mem is not None:
            # EX blocked
            dprint("EX blocked")
            yield PipelineStallEvent(context.exId, self.currentCycle, 'EX', 0)
            return
        
        if inst.isArithmetic or inst.isImmediate:
            # Acquire rd
            self._acquireRegisterLock(node.rd, 2)
        
        result = self._computeEx(inst, rsValue, rtValue)
        rdTarget = context.rdTarget

        if inst.isBranch:
            if result != 0:
                result = self._computeJumpTarget(context.node.target)
                rdTarget = MIPSRegister.PC
            else:
                # Effectively a NOP from here on out
                result = 0
                rdTarget = MIPSRegister.ZERO
        
        # Complete EX
        yield StageAdvanceEvent(context.exId, self.currentCycle, "EX")
        self.pipeline_ex = None
        self.pipeline_mem = EXContext(context, result, rdTarget=rdTarget)
    
    def _applyMEM(self) -> Iterable[LogEvent]:
        context = self.pipeline_mem
        if context is None:
            # MEM empty
            return
        if self.pipeline_wb is not None:
            # MEM blocked
            yield PipelineStallEvent(context.exId, self.currentCycle, 'MEM', 0)
            return

        # Complete MEM
        dprint(f"ADVANCE MEM on {context.exId}")
        yield StageAdvanceEvent(context.exId, self.currentCycle, "MEM")
        self.pipeline_mem = None
        self.pipeline_wb = context
    
    def _applyWB(self) -> Iterable[LogEvent]:
        context = self.pipeline_wb
        if context is None:
            # WB empty
            return
        
        rd = context.rdTarget
        if rd == MIPSRegister.ZERO:
            # Fake-write to $zero
            return True
        
        if (rd == MIPSRegister.PC) and (context.rdValue != self.pc):
            # Flush pipeline
            if self.pipeline_mem is not None:
                yield StageAdvanceEvent(self.pipeline_mem.exId, self.currentCycle, '*')
                yield PipelineExitEvent(self.pipeline_mem.exId, self.currentCycle)
                self.pipeline_mem = None
            if self.pipeline_ex is not None:
                yield StageAdvanceEvent(self.pipeline_ex.exId, self.currentCycle, '*')
                yield PipelineExitEvent(self.pipeline_ex.exId, self.currentCycle)
                self.pipeline_ex = None
            if self.pipeline_id is not None:
                yield StageAdvanceEvent(self.pipeline_id.exId, self.currentCycle, '*')
                yield PipelineExitEvent(self.pipeline_id.exId, self.currentCycle)
                self.pipeline_id = None
            # Flush register locks
            self.registerContention = dict()
        
        self.registers[rd] = context.rdValue

        # Complete WB
        dprint(f"FINISH WB on {context.exId}")
        self.pipeline_wb = None
        yield StageAdvanceEvent(context.exId, self.currentCycle, "WB")
        yield PipelineExitEvent(context.exId, self.currentCycle)
    
    def cycle(self) -> Iterable[LogEvent]:
        # WB Stage
        yield from self._applyWB()
        yield from self._applyMEM()
        yield from self._applyEX()
        yield from self._applyID()
        yield from self._fetchInstruction()

        yield EndOfCycleEvent(self.currentCycle)

        self.currentCycle += 1
