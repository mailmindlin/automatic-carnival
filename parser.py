import re
from ir import MIPSInstruction, Node, MIPSRegister


# TODO: scope?
ARITH_INSTRUCTIONS = {MIPSInstruction.ADD, MIPSInstruction.AND, MIPSInstruction.OR, MIPSInstruction.SLT}
IMMED_INSTRUCTIONS = {MIPSInstruction.ADDI, MIPSInstruction.ANDI, MIPSInstruction.ORI, MIPSInstruction.SLTI}
BRANCH_INSTRUCTIONS = {MIPSInstruction.BEQ, MIPSInstruction.BNE}


class ParseError(Exception):
    """Custom exception for when parsing fails."""
    pass


class Parser(object):
    """ MIPS instruction parser """

    _REGISTER_LUT = {
        '$0': MIPSRegister.ZERO,
        '$zero': MIPSRegister.ZERO,
        '$at': MIPSRegister.AT,
        '$v0': MIPSRegister.V0,
        '$v1': MIPSRegister.V1,
        '$a0': MIPSRegister.A0,
        '$a1': MIPSRegister.A1,
        '$a2': MIPSRegister.A2,
        '$a3': MIPSRegister.A3,
        '$t0': MIPSRegister.T0,
        '$t1': MIPSRegister.T1,
        '$t2': MIPSRegister.T2,
        '$t3': MIPSRegister.T3,
        '$t4': MIPSRegister.T4,
        '$t5': MIPSRegister.T5,
        '$t6': MIPSRegister.T6,
        '$t7': MIPSRegister.T7,
        '$s0': MIPSRegister.S0,
        '$s1': MIPSRegister.S1,
        '$s2': MIPSRegister.S2,
        '$s3': MIPSRegister.S3,
        '$s4': MIPSRegister.S4,
        '$s5': MIPSRegister.S5,
        '$s6': MIPSRegister.S6,
        '$s7': MIPSRegister.S7,
        '$t8': MIPSRegister.T8,
        '$t9': MIPSRegister.T9,
        '$k0': MIPSRegister.K0,
        '$k1': MIPSRegister.K1,
        '$gp': MIPSRegister.GP,
        '$sp': MIPSRegister.SP,
        '$fp': MIPSRegister.FP,
        '$ra': MIPSRegister.RA,
    }

    _INSTRUCTION_LUT = {
        'add': MIPSInstruction.ADD,
        'addi': MIPSInstruction.ADDI,
        'and': MIPSInstruction.AND,
        'andi': MIPSInstruction.ANDI,
        'or': MIPSInstruction.OR,
        'ori': MIPSInstruction.ORI,
        'slt': MIPSInstruction.SLT,
        'slti': MIPSInstruction.SLTI,
        'beq': MIPSInstruction.BEQ,
        'bne': MIPSInstruction.BNE,
    }

    def __init__(self, src):  # type: (str) -> None
        self.src = src
    
    @property
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

    def lookupRegister(self, name):  # type: (str) -> MIPSRegister
        try:
            return Parser._REGISTER_LUT[name]
        except KeyError as e:
            raise ParseError(f"Unknown register: '{name}'") from e
    
    def lookupInstruction(self, name):  # type: (str) -> MIPSInstruction
        try:
            return Parser._INSTRUCTION_LUT[name]
        except KeyError as e:
            raise ParseError(f"Unknown instruction: '{name}'") from e
    
    def buildNode(self, match):  # type: (re.Match) -> Node
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
                inst=inst,
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
                inst=inst,
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
                inst=inst,
                rs=arg1,
                rt=arg2,
                target=target
            )
        else:
            raise ValueError(f'Unexpected instruction: {inst}')

    def __iter__(self):  # type: () -> Iterable[Node]
        for match in re.finditer(self.pattern, self.src):
            yield self.buildNode(match)
