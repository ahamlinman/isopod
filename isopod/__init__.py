import argparse
import logging
import os

from isopod.registry import Registry

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
    parser.add_argument(
        "--db-path",
        type=str,
        help="Path to the SQLite database for state storage",
        default="isopod.sqlite3",
    )
    args = parser.parse_args()

    if os.getuid() != 0:
        log.critical("Not running as root")
        return 1

    registry = Registry(args.db_path)
