import os


def force_unlink(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
