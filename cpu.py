from ir import MIPSInstruction, MIPSRegister, Node
from typing import Dict, List, Optional, Tuple, Iterable
from logger import LogEvent, PipelineStallEvent, PipelineExitEvent, StageAdvanceEvent, InstructionFetchEvent, ExId, EndOfCycleEvent


class PipelineContext(object):
    def __init__(self, exId: ExId, node: Node):
        self.exId = exId
        self.node = node


IFContext = PipelineContext


class IDContext(PipelineContext):
    """
    Fields:
        rsValue
            Value of rs register
        rtValue
            Value of rt register
        rdTarget
            Register to write to
    """
    rsValue: int
    rtValue: int
    rdTarget: MIPSRegister

    def __init__(self, source: IFContext, rsValue: int, rtValue: int, rdTarget: MIPSRegister):
        super().__init__(source.exId, source.node)
        self.rsValue = rsValue
        self.rtValue = rtValue
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
    fwRegValues: Dict[MIPSRegister, int]
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
    
    def _registerDelay(self, *regs: Tuple[MIPSRegister]) -> int:
        result = 0
        for reg in regs:
            delay = self.registerContention.get(reg, 0) - self.currentCycle
            print(f'Delay for {reg!r}: {delay}')
            result = max(result, delay)
        return result
    
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
        context = self.pipeline_id
        if context is None:
            # ID empty
            print("ID empty")
            return
        if self.pipeline_ex is not None:
            # ID blocked
            print("ID blocked")
            yield PipelineStallEvent(context.exId, self.currentCycle, 'ID', 0)
            return
        
        node = context.node
        inst = node.inst

        # Acquire & read input registers
        rsValue = None
        rtValue = None
        in_registers = tuple()
        if inst.isArithmetic or inst.isBranch:
            # Block for rs, rt
            in_registers = (node.rs, node.rt)
            rsValue = self.registers.setdefault(node.rs, 0)
            rtValue = self.registers.setdefault(node.rt, 0)
        elif inst.isImmediate:
            # Block for rs
            in_registers = (node.rs,)
            rsValue = self.registers.setdefault(node.rs, 0)
            rtValue = node.immediate
        
        delay = self._registerDelay(*in_registers)
        if delay > 0:
            # Blocked on input registers
            print(f"ID stall: regs {in_registers}")
            yield PipelineStallEvent(context.exId, self.currentCycle, 'ID', delay)
            return
        
        rdTarget = MIPSRegister.ZERO
        if inst.isArithmetic or inst.isImmediate:
            # Acquire rd
            release = self.currentCycle + 3
            print(f'Lock register {node.rd!r} until cycle {release}')
            self.registerContention[node.rd] = max(self.registerContention.get(node.rd, 0), release)
            #TODO: multiple locks?
            rdTarget = node.rd
        elif inst.isBranch:
            rdTarget = MIPSRegister.PC
        
        # Complete ID
        print("ADVANCE ID")
        yield StageAdvanceEvent(context.exId, self.currentCycle, "ID")
        self.pipeline_id = None
        self.pipeline_ex = IDContext(context, rsValue=rsValue, rtValue=rtValue, rdTarget=rdTarget)
    
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
    
    def _applyEX(self) -> Iterable[LogEvent]:
        context = self.pipeline_ex
        if context is None:
            # EX empty
            print("EX empty")
            return
        if self.pipeline_mem is not None:
            # EX blocked
            print("EX blocked")
            yield PipelineStallEvent(context.exId, self.currentCycle, 'EX', 0)
            return
        
        inst = context.node.inst
        result = self._computeEx(inst, context.rsValue, context.rtValue)
        rdTarget = context.rdTarget

        if inst.isBranch:
            if result != 0:
                # Compute jump target
                try:
                    result = next(i for i, node in enumerate(self.instructions) if node.label == context.node.target)
                except StopIteration:
                    raise RuntimeError(f'Unable to resolve label target: {context.node.target}')
                else:
                    rdTarget = MIPSRegister.PC
            else:
                # Effectively a NOP from here on out
                result = 0
                rdTarget = MIPSRegister.ZERO
        
        # Complete EX
        print("ADVANCE EX")
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
        print(f"ADVANCE MEM on {context.exId}")
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
            print("NEED PIPELINE FLUSH")
        
        self.registers[rd] = context.rdValue

        # Complete WB
        print(f"FINISH WB on {context.exId}")
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
