import argparse
import logging
import os

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%F %T",
)

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Watch the CD-ROM drive and rip every disc to a remote server"
    )
    parser.parse_args()

    if os.getuid() != 0:
        log.critical("Not running as root")
        return 1
