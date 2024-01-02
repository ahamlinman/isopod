import logging
import shlex
import threading
import time
from subprocess import DEVNULL, Popen
from threading import Thread
from typing import Optional

from sqlalchemy import select

import isopod
from isopod import db

log = logging.getLogger(__name__)


class Controller(Thread):
    def __init__(self, target_base: str):
        super().__init__()
        self.target_base = target_base

        self._trigger = threading.Event()

        self._canceled = False

        self._rsync: Optional[Popen] = None
        self._current_path: Optional[str] = None

    def run(self):
        self._trigger.set()
        while self._trigger.wait():
            self._trigger.clear()

            if self._canceled:
                if self._rsync is not None:
                    log.info("Terminating sync")
                    self._rsync.terminate()
                    self._rsync.wait()
                    log.info("Sync terminated")
                return

            if self._rsync is not None:
                if (returncode := self._rsync.poll()) is None:
                    continue
                self._rsync = None
                (path, self._current_path) = (self._current_path, None)
                if returncode == 0:
                    self._handle_send_success(path)
                else:
                    log.info("rsync failed with status %d", returncode)
                    time.sleep(10)  # TODO: Restore exponential backoff.
                    self._trigger.set()
                continue

            if (path := self._get_next_path()) is None:
                log.info("Waiting for next sendable disc")
                continue

            args = ["rsync", "--partial", path, f"{self.target_base}/{path}"]
            self._rsync = Popen(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
            self._current_path = path
            self._poke_on_finish(self._rsync)
            log.info("Started: %s", shlex.join(args))

    def _poke_on_finish(self, proc: Popen):
        def wait_and_poke():
            proc.wait()
            self.poke()

        Thread(target=wait_and_poke, daemon=True).start()

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

    def poke(self):
        self._trigger.set()

    def cancel(self):
        self._canceled = True
        self.poke()
