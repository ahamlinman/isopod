import logging
import math
import shlex
import subprocess
import threading
import time
from subprocess import DEVNULL
from threading import Thread

from sqlalchemy import select

import isopod
from isopod import db

log = logging.getLogger(__name__)
retry_base_sec = 5
retry_max_sec = 300


class Controller(Thread):
    def __init__(self, target_base: str):
        super().__init__(daemon=True)
        self.target_base = target_base.removesuffix("/")
        self.trigger = threading.Event()
        self.retries = 0

    def run(self):
        self.trigger.set()
        while self.trigger.wait():
            if (path := self._get_next_path()) is None:
                log.info("Waiting for next sendable ISO")
                self.trigger.clear()
                continue

            args = ["rsync", "--partial", path, f"{self.target_base}/{path}"]
            log.info("Running: %s", shlex.join(args))
            proc = subprocess.run(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)

            if proc.returncode == 0:
                self.retries = 0
                self._handle_send_success(path)
            else:
                self.retries += 1
                interval = min(
                    retry_max_sec, retry_base_sec * math.pow(2, self.retries - 1)
                )
                log.error(
                    "Sync failed with status %d; waiting %ds", proc.returncode, interval
                )
                time.sleep(interval)

    def poke(self):
        self.trigger.set()

    def _get_next_path(self):
        with db.Session() as session:
            stmt = select(db.Disc).filter_by(status=db.DiscStatus.SENDABLE)
            disc = session.execute(stmt).scalars().first()
            if disc is not None:
                return disc.path

    def _handle_send_success(self, path):
        with db.Session() as session:
            stmt = select(db.Disc).filter_by(path=path)
            disc = session.execute(stmt).scalar_one()
            disc.status = db.DiscStatus.COMPLETE
            session.commit()
            log.info("Finished sending %s", path)

            isopod.force_unlink(path)
            session.delete(disc)
            session.commit()
            log.info("Cleaned up %s", path)
