import sys

def main(srcFile):
    with open(srcFile, 'r') as f:
        # TODO: read src
        pass
    # Parse
    # Run the thing


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: automatic-carnival [src]')
        exit(-1)

    main(sys.argv[1])