import re
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


# TODO: scope?
ARITH_INSTRUCTIONS = {MIPSInstruction.ADD, MIPSInstruction.AND, MIPSInstruction.OR, MIPSInstruction.SLT}
IMMED_INSTRUCTIONS = {MIPSInstruction.ADDI, MIPSInstruction.ANDI, MIPSInstruction.ORI, MIPSInstruction.SLTI}
BRANCH_INSTRUCTIONS = {MIPSInstruction.BEQ, MIPSInstruction.BNE}


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


class ParseError(Exception):
    """Custom exception for when parsing fails."""
    pass


class Parser(object):
    def __init__(self, src):  # type: (str) -> Any
        self.src = src
    
    def pattern(self):
        """
        Build parser pattern.

        Pattern provides the following named groups:
            text
                Full (raw) text of instruction, not including the label
            label (optional)
                Label attached to instruction
            inst
                Text of instruction
            arg1
                First argument register
            arg2
                Second argument register
            arg3 (optional)
                Third argument register
            immediate (optional)
                Immediate value
            target (optional)
                Jump target label
        """
        label_pattern = '\\w+'
        inst_pattern = '\\w+'
        reg_pattern = '\\$(?:\\d{1,2}|zero|a[t0-3]|[kv][01]|t[0-9]|s[0-7]|[gsf]p|ra)'
        immediate_pattern = '\\d+'
        return re.compile(f'^\\s*(?:(?P<label>{label_pattern}):)?\\s*(?P<text>(?P<inst>{inst_pattern})\\s+(?P<arg1>{reg_pattern})\\s*,\\s*(?P<arg2>{reg_pattern})\\s*,\\s*(?:(?P<arg3>{reg_pattern})|(?P<immediate>{immediate_pattern})|(?P<target>{label_pattern})))\\s*$', flags=re.MULTILINE)
    
    def lookupRegister(self, name):
        if name == '$zero':
            return 0
        raise ValueError(f'Unknown register name: {name}')
    
    def buildNode(self, match):
        inst_name = match['inst']
        try:
            inst = MIPSInstruction[inst_name.upper()]
        except KeyError as e:
            raise ParseError(f"Unknown instruction '{inst_name}'") from e
        
        # Args 1 & 2 are always registers
        arg1 = self.lookupRegister(match['arg1'])
        arg2 = self.lookupRegister(match['arg2'])
        if inst in ARITH_INSTRUCTIONS:
            arg3 = self.lookupRegister(match['arg3'])
            return Node(
                text=match['text'],
                label=match['label'],
                rd=arg1,
                rs=arg2,
                rt=arg3
            )
        elif inst in IMMED_INSTRUCTIONS:
            try:
                immediate = int(match['immediate'])
            except ValueError as e:
                raise ParseError(f"Unable to parse immediate (value: {match['immediate']})") from e

            return Node(
                text=match['text'],
                label=match['label'],
                rs=arg1,
                rt=arg2,
                immediate=immediate
            )
        elif inst in BRANCH_INSTRUCTIONS:
            target = match['target']
            if target is None:
                raise ValueError("Missing target in instruction '{match['text']}'")
            return Node(
                text=match['text'],
                label=match['label'],
                rs=arg1,
                rt=arg2,
                target=target
            )
        else:
            raise ValueError(f'Unexpected instruction: {inst}')

    def __iter__(self):
        for match in re.finditer(self.pattern, self.src):
            yield self.buildNode(match)
