import logging
import os
import os.path
import shutil
import signal
import sys
import threading

import click
from sqlalchemy import create_engine, select

import isopod.linux
import isopod.ripper
import isopod.sender
from isopod import db


def _die_on_thread_exception(args):
    threading.__excepthook__(args)  # type: ignore
    os._exit(100)


threading.excepthook = _die_on_thread_exception

logging.basicConfig(
    level=logging.INFO,
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
@click.option(
    "--min-free-bytes",
    type=int,
    default=5 * (1024**3),
    help="Only rip when this much space will be free after",
)
def main(workdir, device, target, min_free_bytes):
    """Watch a CD-ROM drive and rip every disc to a remote server."""

    required_cmds = ("ddrescue", "rsync")
    missing_cmds = [cmd for cmd in required_cmds if shutil.which(cmd) is None]
    if missing_cmds:
        log.critical("Missing required commands: %s", missing_cmds)
        log.critical("Isopod needs these installed to rip and send discs")
        sys.exit(1)

    if isopod.linux.get_diskseq(device) is None:
        log.critical("%s has no diskseq property in udev", device)
        log.critical("Isopod will behave erratically in this configuration")
        log.critical("Try a newer kernel, systemd, udev, etc.")
        sys.exit(1)

    workdir = os.path.abspath(workdir)
    log.info("Entering workdir: %s", workdir)
    os.chdir(workdir)

    db.setup(create_engine(f"sqlite+pysqlite:///isopod.sqlite3"))
    cleanup_stale_discs()

    sender = isopod.sender.Sender(target)
    ripper = isopod.ripper.Ripper(
        device_path=device,
        min_free_bytes=min_free_bytes,
        on_status_change=lambda: log.info("Ripper status: %s", ripper.status),
        on_rip_success=sender.poll,
    )

    # TODO: A status layer that can handle refreshing a small display.

    wait_for_any_signal_once(signal.SIGINT, signal.SIGTERM)
    log.info("Received stop signal, shutting down")
    sender.cancel()
    ripper.cancel()


def force_unlink(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def cleanup_stale_discs():
    with db.Session() as session:
        stmt = select(db.Disc).where(
            db.Disc.status.in_((db.DiscStatus.RIPPABLE, db.DiscStatus.COMPLETE))
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
