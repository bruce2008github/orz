if __name__ == '__main__':
    import os.path
    import sys

    from .runtime import loadfile

    loadfile(os.path.abspath(sys.argv[1]))()
