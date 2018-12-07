import re
from ir import MIPSInstruction, Node


# TODO: scope?
ARITH_INSTRUCTIONS = {MIPSInstruction.ADD, MIPSInstruction.AND, MIPSInstruction.OR, MIPSInstruction.SLT}
IMMED_INSTRUCTIONS = {MIPSInstruction.ADDI, MIPSInstruction.ANDI, MIPSInstruction.ORI, MIPSInstruction.SLTI}
BRANCH_INSTRUCTIONS = {MIPSInstruction.BEQ, MIPSInstruction.BNE}


class ParseError(Exception):
    """Custom exception for when parsing fails."""
    pass


class Parser(object):
    """ MIPS instruction parser """
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

    def __iter__(self):  # type: () -> Iterable[Node]
        for match in re.finditer(self.pattern, self.src):
            yield self.buildNode(match)
