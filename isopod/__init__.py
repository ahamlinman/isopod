import argparse
import logging
import os

from sqlalchemy import create_engine

import isopod.store
from isopod.store import Disc, DiscStatus

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%F %T",
)

# Work around SQLAlchemy adding their own handler for echo=True, even though we
# already have one at the root.
logging.getLogger("sqlalchemy.engine.Engine").addHandler(logging.NullHandler())

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

    engine = create_engine(f"sqlite+pysqlite:///{args.db_path}", echo=True)
    isopod.store.Session.configure(bind=engine)
    isopod.store.Base.metadata.create_all(engine)

    with isopod.store.Session() as session:
        with session.begin():
            session.add(Disc(name="ISOTEST", status=DiscStatus.RIPPABLE))
