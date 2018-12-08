"""Contains IR structures."""

from enum import Enum, IntEnum
from typing import Optional

#enumerate registers
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

    PC = 64

    def __str__(self) -> str:
        return '$' + self.name.lower()

#enumerate instructions
class MIPSInstruction(Enum):
    NOP  = 0
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
    
    @property
    def isArithmetic(self):
        """Predicate for if instruction matches form `INST rd,rs,rt`"""
        return self in (MIPSInstruction.ADD, MIPSInstruction.AND, MIPSInstruction.OR, MIPSInstruction.SLT)
    
    @property
    def isImmediate(self):
        """Predicate for if instruction matches form `INST rd,rs,imm`"""
        return self in (MIPSInstruction.ADDI, MIPSInstruction.ANDI, MIPSInstruction.ORI, MIPSInstruction.SLTI)

    @property
    def isBranch(self):
        """Predicate for if instruction matches form `INST rs,rt,target`"""
        return self in (MIPSInstruction.BEQ, MIPSInstruction.BNE)

    def __str__(self):
        return self.name.lower()

#MIPS instruction container class
class Node(object):
    """
    MIPS instruction IR
    """
    def __init__(
            self,
            *,
            text: Optional[str] = None,
            label: Optional[str] = None,
            inst: MIPSInstruction,
            rd: Optional[MIPSInstruction] = None,
            rs: MIPSInstruction,
            rt: Optional[MIPSInstruction] = None,
            immediate: Optional[int] = None,
            target: Optional[str] = None
    ):
        self.text = text
        self.label = label
        self.inst = inst
        self.rd = rd
        self.rs = rs
        self.rt = rt
        self.immediate = immediate
        self.target = target
    
    #return instruction as a string (formatted for output)
    def _asText(self) -> str:
        inst = self.inst
        if inst == MIPSInstruction.NOP:
            return 'nop'
        elif inst.isArithmetic:
            return f'{inst!s} {self.rd!s},{self.rs!s},{self.rt!s}'
        elif inst.isImmediate:
            return f'{inst!s} {self.rd!s},{self.rs!s},{self.immediate}'
        elif inst.isBranch:
            return f'{inst!s} {self.rs!s},{self.rt!s},{self.target}'
        else:
            raise ValueError(f'Unexpected instruction {inst}')

    #formatted string representation
    def __str__(self):
        """Reconstruct assembly text"""
        if self.text is None:
            self.text = self._asText()
        return self.text

    #unformatted string representation
    def __repr__(self):
        args = []
        if self.text is not None:
            args.append(f'text={self.text!r}')
        if self.label is not None:
            args.append(f'label={self.label!r}')
        args.append(f'inst={self.inst.name}')
        if self.rd is not None:
            args.append(f'rd={self.rd.name}')
        if self.rs is not None:
            args.append(f'rs={self.rs.name}')
        if self.rt is not None:
            args.append(f'rt={self.rt.name}')
        if self.immediate is not None:
            args.append(f'immediate={self.immediate!r}')
        if self.target is not None:
            args.append(f'target={self.target!r}')
        return f"Node({', '.join(args)})"
