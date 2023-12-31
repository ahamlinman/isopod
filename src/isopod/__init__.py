import logging
import os
import os.path
import shutil
import signal
import threading

import click
from sqlalchemy import create_engine, select

import isopod.ripper
import isopod.sender
import isopod.store
from isopod.store import Disc, DiscStatus, Session

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

    for cmd in ("ddrescue", "rsync"):
        if shutil.which(cmd) is None:
            log.critical("Cannot find %s in $PATH", cmd)
            os.exit(1)

    workdir = os.path.abspath(workdir)
    log.info("Entering workdir: %s", workdir)
    os.chdir(workdir)

    isopod.store.setup(create_engine(f"sqlite+pysqlite:///isopod.sqlite3"))
    cleanup_stale_discs()

    sender = isopod.sender.Controller(target)
    sender.start()

    ripper = isopod.ripper.Controller(device, sender.poke)
    ripper.start()

    wait_for_any_signal_once(signal.SIGINT, signal.SIGTERM)
    log.info("Signaled to stop; waiting for any active rip to finish")


def force_unlink(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def cleanup_stale_discs():
    with Session() as session:
        stmt = select(Disc).where(
            Disc.status.in_((DiscStatus.RIPPABLE, DiscStatus.COMPLETE))
        )
        for disc in session.execute(stmt).scalars():
            force_unlink(disc.path)
            session.delete(disc)
            session.commit()
            log.info("Cleaned up stale disc %s", disc.path)


def wait_for_any_signal_once(*args):
    evt = threading.Event()
    originals = {sig: signal.signal(sig, lambda *_: evt.set()) for sig in args}
    evt.wait()
    for sig, handler in originals.items():
        signal.signal(sig, handler)
