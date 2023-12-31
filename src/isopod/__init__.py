import logging
import os
import os.path
import threading

import click
from sqlalchemy import create_engine

import isopod.ripper
import isopod.sender
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
    "--workdir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
    default=".",
    help="The directory to stage ISOs and track their status",
)
@click.option(
    "--device",
    type=click.Path(exists=True, readable=True),
    default="/dev/cdrom",
    help="The CD-ROM drive to rip from",
)
@click.option(
    "--target", type=str, required=True, help="The base rsync target to receive ISOs"
)
def main(workdir, device, target):
    """Watch a CD-ROM drive and rip every disc to a remote server."""

    workdir = os.path.abspath(workdir)
    log.info("Entering workdir: %s", workdir)
    os.chdir(workdir)

    # TODO: Remove echo=True at some point when things are more stable.
    isopod.store.setup(create_engine(f"sqlite+pysqlite:///isopod.sqlite3", echo=True))

    sender = isopod.sender.Controller(target)
    sender.start()

    ripper = isopod.ripper.Controller(device, sender.poke)
    ripper.start()

    # TODO: Something other than blocking forever, e.g. wait for a signal and
    # let all remaining rips finish.
    threading.Event().wait()
