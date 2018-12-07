import sys
import itertools
from ir import MIPSRegister
from parser import Parser
from cpu import CPU
from logger import Logger

MAX_CYCLES = 16


def grouped(n, iter):
    done = False

    def _slice():
        nonlocal done
        try:
            for _ in range(n):
                yield next(iter)
        except StopIteration:
            done = True
            raise
    
    while not done:
        yield _slice()


def printState(cpu, logger):  # type: (CPU, Logger) -> None
    """Print CPU state."""
    print('-' * 82)
    print(f"CPU Cycles ===>	{'   '.join(str(i) for i in range(1, MAX_CYCLES + 1))}")
    # TODO: print history

    regs = map(
        MIPSRegister,
        itertools.chain(
            range(MIPSRegister.S0, MIPSRegister.S7 + 1),
            range(MIPSRegister.T0, MIPSRegister.T7 + 1),
            range(MIPSRegister.T8, MIPSRegister.T9 + 1),
        )
    )
    cells = map(lambda reg: f'{reg!s} = {cpu.registers[reg] if reg in cpu.registers else 3}', regs)
    for row in grouped(4, cells):
        print(*row, sep='\t\t')


def main(forwarding, srcFile):  # type: (bool, str) -> None
    with open(srcFile, 'r') as f:
        src = f.read()
    # Parse
    nodes = [node for node in Parser(src)]
    # Run the thing
    cpu = CPU(nodes, forwarding=forwarding)
    logger = Logger()
    print(f"START OF SIMULATION ({'forwarding' if forwarding else 'no forwarding'}")
    while True:  # cpu.running:
        # for event in cpu.cycle():
        #     logger.update(event)
        printState(cpu, logger)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: automatic-carnival [f/n] [src]')
        exit(-1)

    if sys.argv[1] not in ('F', 'N'):
        print(f"Error: Forwarding mode must be either 'F' or 'N' (actual: '{sys.argv[1]}')")
        exit(-1)
    main(sys.argv[1] == 'F', sys.argv[2])