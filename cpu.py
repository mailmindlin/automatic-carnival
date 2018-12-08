from ir import MIPSInstruction, MIPSRegister, Node
from typing import Dict, List, Optional, Tuple, Iterable
from logger import LogEvent, PipelineStallEvent, StageAdvanceEvent, InstructionFetchEvent, ExId, EndOfCycleEvent


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
        return max(0, *regs, key=lambda reg: self.registerContention[reg] - self.cycle)
    
    def _fetchInstruction(self) -> Optional[IFContext]:
        pc = self.pc
        if pc >= len(self.instructions):
            return None
        
        node = self.instructions[pc]
        exId = self.nextExId
        self.nextExId += 1
        self.pc = pc + 1

        return IFContext(exId, node)
    
    def _applyID(self, context: IFContext) -> Optional[IDContext]:
        node = context.node
        inst = node.inst

        rsValue = None
        rtValue = None
        if inst.isArithmetic or inst.isBranch:
            # Block for rs, rt
            if self._registerDelay(node.rs, node.rt) > 0:
                #TODO: generate n-nop event
                return None
            rsValue = self.registers.setdefault(node.rs, 0)
            rtValue = self.registers.setdefault(node.rt, 0)
        elif inst.isImmediate:
            # Block for rs
            if self._registerDelay(node.rs) > 0:
                #TODO: generate n-nop event
                return None
            rtValue = node.immediate
            pass
        
        rdTarget = MIPSRegister.ZERO
        if inst.isArithmetic or inst.isImmediate:
            # Acquire rd
            #TODO
            rdTarget = node.rd
        elif inst.isBranch:
            rdTarget = MIPSRegister.PC
        
        return IDContext(context, rsValue=rsValue, rtValue=rtValue, rdTarget=rdTarget)
    
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
    
    def _applyEX(self, context: IDContext) -> EXContext:
        # TODO: emulate EX stage
        inst = context.node.inst
        result = self._computeEx(inst, context.rsValue, context.rtValue)

        if inst.isBranch:
            if result != 0:
                # Compute jump target
                try:
                    target = next(i for i, node in enumerate(self.instructions) if node.label == context.node.target)
                except StopIteration:
                    raise RuntimeError(f'Unable to resolve label target: {context.node.target}')
                return EXContext(context, target, MIPSRegister.PC)
            else:
                # Effectively a NOP from here on out
                return EXContext(context, 0, MIPSRegister.ZERO)
        
        return EXContext(context, result)
    
    def _applyMEM(self, context: EXContext) -> MEMContext:
        return context
    
    def _applyWB(self, context: MEMContext) -> bool:
        rd = context.rdTarget
        if rd == MIPSRegister.ZERO:
            # Fake-write to $zero
            return True
        #TODO: finish
        return True
    
    def cycle(self) -> Iterable[LogEvent]:
        # WB Stage
        if self.pipeline_wb is not None:
            if self._applyWB(self.pipeline_wb):
                # yield PipelineExitEvent(self.pipeline_wb.exId, self.currentCycle)
                self.pipeline_wb = None
            else:
                # Write failed
                #TODO: can this happen?
                pass
        
        # MEM Stage
        if self.pipeline_mem is not None:
            res = self._applyMEM(self.pipeline_mem) if self.pipeline_wb is None else None
            if res is not None:
                self.pipeline_mem = None
                self.pipeline_wb = res
                yield StageAdvanceEvent(res.exId, self.currentCycle, "MEM")
            else:
                # Pipeline stall
                #TODO
                pass
        
        # EX Stage
        if self.pipeline_ex is not None:
            res = self._applyEX(self.pipeline_ex) if self.pipeline_mem is None else None
            if res is not None:
                self.pipeline_ex = None
                self.pipeline_mem = res
                yield StageAdvanceEvent(res.exId, self.currentCycle, "EX")
            else:
                # Pipeline stall
                #TODO
                pass
        
        # ID Stage
        if self.pipeline_id is not None:
            res = self._applyEX(self.pipeline_id) if self.pipeline_ex is None else None
            if res is not None:
                self.pipeline_id = None
                self.pipeline_ex = res
                yield StageAdvanceEvent(res.exId, self.currentCycle, "ID")
            else:
                # Pipeline stall
                #TODO
                pass
        
        # IF Stage
        if self.pipeline_id is None:
            res = self._fetchInstruction()
            if res is not None:
                self.pipeline_id = res
                yield InstructionFetchEvent(res.exId, self.currentCycle, "IF")

        yield EndOfCycleEvent(self.currentCycle)

        self.currentCycle += 1
