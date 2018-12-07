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
                       List[Node, List[number], number]
                      ]
        instructions: List[Node]
        PC: number
        forwarding: bool
    """
    def execute(self, instruction):
        if instruction.isBranch:
            if instruction.label == BEQ:
                if instruction.rd == instruction.rs:
                    return 1
                return 0

            if instruction.label == BNE:
                if instruction.rd != instruction.rs:
                    return 1
                return 0

        elif instruction.isArithmetic:
            if instruction.label == ADD:
                return instruction.rs + instruction.rt

            if instruction.label == AND:
                #is this bitwise AND in python??
                return instruction.rs & instruction.rt

            if instruction.label == OR:
                #same as above
                return instruction.rs | instruction.rt

            if instruction.label == SLT:
                return min([instruction.rs, instruction.rt])
        else:
            if instruction.label == ADDI:
                return instruction.rs + instruction.immediate

            if instruction.label == ANDI:
                #is this bitwise AND in python??
                return instruction.rs & instruction.immediate

            if instruction.label == ORI:
                #same as above
                return instruction.rs | instruction.immediate

            if instruction.label == SLTI:
                return min([instruction.rs, instruction.immediate])


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
                        if newStage == EX:
                            instruction[2] = execute(instruction[0])
                            
                        if newStage == WB:
                            if instruction[0].isBranch:
                                #well fuck

                            

                            else:
            yield #the CPU object??? is that how you do this
            PC+=1;

