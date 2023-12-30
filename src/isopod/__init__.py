import logging
import os
import os.path
import threading
from typing import Optional

import click
from sqlalchemy import create_engine

import isopod.ripper
import isopod.store

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%F %T",
)


# Work around SQLAlchemy adding their own handler for echo=True, even though we
# already have one at the root.
logging.getLogger("sqlalchemy.engine.Engine").addHandler(logging.NullHandler())

log = logging.getLogger(__name__)
context_settings = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=context_settings)
@click.option(
    "--device", type=str, default="/dev/cdrom", help="The CD-ROM drive to rip from"
)
@click.option(
    "--workdir",
    type=str,
    default=".",
    help="The directory to stage ripped ISOs and track their status",
)
def main(device, workdir):
    """Watch a CD-ROM drive and rip every disc to a remote server."""

    if os.getuid() != 0:
        log.critical("Not running as root")
        return 1

    # TODO: Remove echo=True at some point when things are more stable.
    db_path = os.path.join(workdir, "isopod.sqlite3")
    isopod.store.setup(create_engine(f"sqlite+pysqlite:///{db_path}", echo=True))

    ripper = isopod.ripper.Controller(device, workdir)
    ripper.start()

    # TODO: Something other than blocking forever, e.g. wait for a signal and
    # let all remaining rips finish.
    threading.Event().wait()
