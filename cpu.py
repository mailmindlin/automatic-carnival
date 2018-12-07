from ir import MIPSInstruction, MIPSRegister, Node
from typing import Dict, List, Optional, Tuple, Iterable
from logger import LogEvent, PipelineExitEvent, PipelineStallEvent, StageAdvanceEvent, InstructionFetchEvent, ExId


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
        return super().__init__(source.exId, source.node)
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
        return super().__init__(source.exId, source.node)
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


    def __init__(self, src):
        self.src = src

    
    def updateCycle(self):
        """PC=0"""
        while True:
            #all occupied stages empty out at the beginning of a cycle
            for stage in pipeStages:
                stage = False

            #fetch new instruction
            pipeline.append([instructions[i], [0 for number in xrange(PC)]])

            for instruction in pipeline:
                #if the instruction is incomplete
                if max(instruction[1]!=WB):
                    #if the next pipeline stage is free
                    if !pipeStages[max(instruction[1])]:
                        #put the instruction through the next pipeline stage
                        newStage = max(instruction[1])+1
                        instruction[1].append(newStage)
                        pipeStages[max(newStage)] = True
                        if newStage == ID:
                        if newStage == EX && forwarding:
                            execute(instruction[0])
                            #store your output somewhere relevant
                            
                        if newStage == WB:

            PC+=1;

