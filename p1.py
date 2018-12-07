import sys
from parser import Parser


def main(forwarding, srcFile):  # type: (bool, str) -> None
    with open(srcFile, 'r') as f:
        src = f.read()
    # Parse
    nodes = [node for node in Parser(src)]
    # Run the thing


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: automatic-carnival [f/n] [src]')
        exit(-1)

    if sys.argv[1] not in ('F', 'N'):
        print(f"Error: Forwarding mode must be either 'F' or 'N' (actual: '{sys.argv[1]}')")
        exit(-1)
    main(sys.argv[1] == 'F', sys.argv[2])