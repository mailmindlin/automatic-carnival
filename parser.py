
class MIPSInstruction(object):
    """MIPS instruction IR"""
    def __init__(self, inst, rd, rs, rt, label=None, immediate=None):
        self.inst = inst
        self.rd = rd
        self.rs = rs
        self.rt = rt
        self.label = label
        self.immediate = immediate
    def __str__(self):
        """Reconstruct assembly text"""
        # TODO: impl
        raise NotImplementedError("Please finish")

def parse(src):
    # TODO: impl
    raise NotImplementedError("Please finish")