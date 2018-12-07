"""Contains IR structures."""

from enum import Enum, IntEnum


class MIPSRegister(IntEnum):
    ZERO = 0
    AT = 1
    V0 = 2
    V1 = 3
    A0 = 4
    A1 = 5
    A2 = 6
    A3 = 7
    T0 = 8
    T1 = 9
    T2 = 10
    T3 = 11
    T4 = 12
    T5 = 13
    T6 = 14
    T7 = 15
    S0 = 16
    S1 = 17
    S2 = 18
    S3 = 19
    S4 = 20
    S5 = 21
    S6 = 22
    S7 = 23
    T8 = 24
    T9 = 25
    K0 = 26
    K1 = 27
    GP = 28
    SP = 29
    FP = 30
    RA = 31

    def __str__(self):
        # TODO: finish
        pass


class MIPSInstruction(Enum):
    ADD  = 1
    AND  = 2
    OR   = 3
    SLT  = 4
    BEQ  = 5
    BNE  = 6
    ADDI = 7
    ANDI = 8
    ORI  = 9
    SLTI = 10


class Node(object):
    """
    MIPS instruction IR
    """
    def __init__(self, *, text=None, label=None, inst, rd=None, rs, rt, immediate=None, target=None):
        """
        Parameters:
        text: str?
            Raw text
        label: str?
            Instruction label name
        inst: MIPSInstruction
        rd: MIPSRegister?
        rs: MIPSRegister
        rt: MIPSRegister
        immediate: int?
            Immediate value
        """
        self.text = text
        self.label = label
        self.inst = inst
        self.rd = rd
        self.rs = rs
        self.rt = rt
        self.immediate = immediate
        self.target = target
    
    def __str__(self):
        """Reconstruct assembly text"""
        # TODO: impl
        raise NotImplementedError("Please finish")
