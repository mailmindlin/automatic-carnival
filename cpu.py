from enum import Enum

class TimingEvent(object):
    pass

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
    """


    def __init__(self, src):
        self.src = src

    
    def updateCycle(self):
        """PC=0"""
        while True:
            if !pipeStages[FX]:
                pipeline.append([instructions[i], [0 for number in xrange(PC)]])

            for instruction in pipeline:
                #if the instruction is incomplete, and the next pipeline stage for the instruction is free
                if max(instruction[1]!=WB) && pipeStages[max(instruction[1])]: 
                    instruction[1].append()
            PC+=1;

