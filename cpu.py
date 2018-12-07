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
                        #if after doing so 
                        if 
            PC+=1;

