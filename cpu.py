"""Contains stuff to emulate a MIPS CPU with 5-stage pipeline."""
from ir import MIPSInstruction, MIPSRegister, Node
from typing import Dict, List, Optional, Tuple, Iterable
from logger import LogEvent, PipelineStallEvent, PipelineExitEvent, StageAdvanceEvent, InstructionFetchEvent, ExId, EndOfCycleEvent


class PipelineContext(object):
    """Used for data stored in each stage of the pipeline."""

    def __init__(self, exId: ExId, node: Node):
        self.exId = exId
        self.node = node


IFContext = PipelineContext


class IDContext(PipelineContext):
    """
    Used for data passed from ID -> EX.

    Fields
    ------
    rdTarget: MIPSRegister
        Register to write to
    stalled: bool
        Track if NOP's have already been generated for this stage
    
    """

    rdTarget: MIPSRegister
    stalled: bool = False

    def __init__(self, source: IFContext, rdTarget: MIPSRegister):
        super().__init__(source.exId, source.node)
        self.rdTarget = rdTarget


class EXContext(PipelineContext):
    """
    Context passed from EX -> MEM -> WB.

    Fields
    ------
    rdValue: int
        Computed output value
    rdTarget: MIPSRegister
        Register to write to
    """

    rdValue: int
    rdTarget: MIPSRegister

    def __init__(self, source: IDContext, rdValue: int, rdTarget: Optional[MIPSRegister] = None):
        """
        Create EXContext.

        Parameters
        ----------
        source: IDContext
            Previous stage's context
        rdValue: int
            Computed rD value
        rdTarget: MIPSRegister?
            Override write target
        
        """
        super().__init__(source.exId, source.node)
        self.rdValue = rdValue
        self.rdTarget = rdTarget or source.rdTarget


MEMContext = EXContext


class CPU(object):
    """
    MIPS CPU emulator.

    Events are generated each cycle which can help diagram the state of the CPU.

    Fields
    ------
    forwarding: bool
        Whether or not to enable register forwarding
    currentCycle: int
        Current cycle number (starting at 0)
    registers: Dict[MIPSRegister, int]
        Register name->value lookup
    registerAvailability: Dict[MIPSRegister, int]
        LUT of when registers will become available again
    instructions: List[Node]
        Source instruction list
    nextExId: ExId
        Tracks next ExId to issue
    pipeline_id: Optional[IFContext]
        IF -> ID pipeline storage
    pipeline_ex: Optional[IDContext]
        ID -> EX pipeline storage
    pipeline_mem: Optional[EXContext]
        EX -> MEM pipeline storage
    pipeline_wb: Optional[MEMContext]
        MEM -> WB pipeline storage
    
    """
    
    forwarding: bool
    currentCycle: int
    registers: Dict[MIPSRegister, int]
    registerAvailability: Dict[MIPSRegister, int]
    instructions: List[Node]
    nextExId: ExId

    # Pipeline
    pipeline_id: Optional[IFContext]
    pipeline_ex: Optional[IDContext]
    pipeline_mem: Optional[EXContext]
    pipeline_wb: Optional[MEMContext]

    def __init__(self, src: List[Node], forwarding: bool):
        """
        Construct CPU from source.

        Parameters
        ----------
        src: List[Node]
            Source nodes
        forwarding: bool
            Whether or not to enable register forwarding
        
        """
        self.instructions = src
        self.forwarding = forwarding
        self.registers = {}
        self.registerAvailability = {}
        self.nextExId = 0
        self.currentCycle = 0
        self.pipeline_id = None
        self.pipeline_ex = None
        self.pipeline_mem = None
        self.pipeline_wb = None
    
    @property
    def pc(self) -> int:
        """Get program counter."""
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
    
    def register(self, reg: MIPSRegister) -> int:
        """Lookup a register's value."""
        return self.registers.setdefault(reg, 0)
    
    def _applyIF(self) -> Iterable[LogEvent]:
        """Run the IF stage."""
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
            return
        if self.pipeline_ex is not None:
            # ID blocked (EX filled)
            yield PipelineStallEvent(context.exId, self.currentCycle, 'IF', 0)
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
        available = self.registerAvailability.get(reg, 0)
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
        Get EX inputs & availability.

        This method is only guarunteed to return valid things for calls from the EX stage.

        Parameters
        ----------
        node: Node
            Source node
        
        Returns
        -------
        int
            First cycle that rS and rT are available
        int
            rS value
        int
            rT value
        
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
        """
        Acquire lock on output register.

        Parameters
        ----------
        reg: MIPSRegister
            Register to lock
        duration: int
            Number of cycles to lock for (starting at 0 = currentCycle)
        
        """
        if reg in (MIPSRegister.ZERO, MIPSRegister.PC):
            # You can't acquire these
            return
        releaseCycle = max(self.registerAvailability.get(reg, 0), self.currentCycle + duration)
        self.registerAvailability[reg] = releaseCycle
    
    def _computeEx(self, inst: MIPSInstruction, rS: int, rT: int) -> int:
        """
        Actually compute the result of EX.

        Parameters
        inst: MIPSInstruction
            Instruction
        rS: int
            First parameter
        rT: int
            Second parameter
        
        Returns
        -------
        int
            Computed result
        
        """
        if inst in (MIPSInstruction.ADD, MIPSInstruction.ADDI):
            return rS + rT
        elif inst in (MIPSInstruction.AND, MIPSInstruction.ANDI):
            return rS & rT
        elif inst in (MIPSInstruction.OR, MIPSInstruction.ORI):
            return rS | rT
        elif inst in (MIPSInstruction.SLT, MIPSInstruction.SLTI):
            return 1 if (rS < rT) else 0
        elif inst == MIPSInstruction.BEQ:
            return 1 if (rS == rT) else 0
        elif inst == MIPSInstruction.BNE:
            return 1 if (rS != rT) else 0
        else:
            raise ValueError("Unknown instruction")
    
    def _computeJumpTarget(self, target: str) -> int:
        """
        Compute jump address with O(n) lookup.

        Parameters
        ---------
        target: str
            Target label
        
        Returns
        -------
        int
            Address of labelled instruction
        
        """
        try:
            return next(i for i, node in enumerate(self.instructions) if node.label == target)
        except StopIteration:
            raise RuntimeError(f'Unable to resolve label target: {target}')
        
    def _applyEX(self) -> Iterable[LogEvent]:
        """Apply EX stage, and get events."""
        context = self.pipeline_ex
        if context is None:
            # EX empty
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
            yield PipelineStallEvent(context.exId, self.currentCycle, 'ID', 0)
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
        """Apply MEM stage, and get events."""
        context = self.pipeline_mem
        if context is None:
            # MEM empty
            return
        if self.pipeline_wb is not None:
            # MEM blocked
            yield PipelineStallEvent(context.exId, self.currentCycle, 'EX', 0)
            return

        # Complete MEM
        yield StageAdvanceEvent(context.exId, self.currentCycle, "MEM")
        self.pipeline_mem = None
        self.pipeline_wb = context  # No changes here
    
    def _applyWB(self) -> Iterable[LogEvent]:
        """Apply WB stage, and get events."""
        context = self.pipeline_wb
        if context is None:
            # WB empty
            return
        
        rd = context.rdTarget
        if (rd == MIPSRegister.PC) and (context.rdValue != self.pc):
            # Flush pipeline if we're altering the PC
            if self.pipeline_mem is not None:
                yield StageAdvanceEvent(self.pipeline_mem.exId, self.currentCycle, '*')
                self.pipeline_mem = None
            if self.pipeline_ex is not None:
                yield StageAdvanceEvent(self.pipeline_ex.exId, self.currentCycle, '*')
                self.pipeline_ex = None
            if self.pipeline_id is not None:
                yield StageAdvanceEvent(self.pipeline_id.exId, self.currentCycle, '*')
                self.pipeline_id = None
            # Flush register locks
            self.registerAvailability = dict()
        
        if rd != MIPSRegister.ZERO:  # Don't actually write to $zero
            self.registers[rd] = context.rdValue

        # Complete WB
        self.pipeline_wb = None
        yield StageAdvanceEvent(context.exId, self.currentCycle, "WB")
        yield PipelineExitEvent(context.exId, self.currentCycle)
    
    def cycle(self) -> Iterable[LogEvent]:
        # WB Stage
        yield from self._applyWB()
        yield from self._applyMEM()
        yield from self._applyEX()
        yield from self._applyID()
        yield from self._applyIF()

        yield EndOfCycleEvent(self.currentCycle)

        self.currentCycle += 1
