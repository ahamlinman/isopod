import logging
import os
import subprocess
import threading
import time
from subprocess import DEVNULL
from threading import Thread

from sqlalchemy import select

from isopod.store import Disc, DiscStatus, Session

log = logging.getLogger(__name__)


class Controller(Thread):
    def __init__(self, target_base: str):
        super().__init__(daemon=True)

        if not target_base.endswith("/"):
            target_base += "/"

        self.target_base = target_base
        self.poke = threading.Event()

    def run(self):
        self.poke.set()
        while self.poke.wait():
            if (path := self._get_next_path()) is None:
                log.info("Waiting for next sendable ISO")
                self.poke.clear()
                continue

            args = ["rsync", "--partial", path, f"{self.target_base}/{path}"]
            log.info("Starting sync: %s", args)
            proc = subprocess.run(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)

            if proc.returncode == 0:
                self._handle_send_success(path)
            else:
                log.error("Sync failed with status %d", proc.returncode)
                time.sleep(10)

    def _get_next_path(self):
        with Session() as session:
            stmt = select(Disc).filter_by(status=DiscStatus.SENDABLE)
            disc = session.execute(stmt).scalars().first()
            if disc is not None:
                return disc.path

    def _handle_send_success(self, path):
        with Session() as session:
            stmt = select(Disc).filter_by(path=path)
            disc = session.execute(stmt).scalar_one()
            disc.status = DiscStatus.COMPLETE
            session.commit()
            log.info("Finished sending %s", path)

            try:
                os.unlink(path)
            except FileNotFoundError:
                pass

            session.delete(disc)
            session.commit()
            log.info("Cleaned up %s", path)
