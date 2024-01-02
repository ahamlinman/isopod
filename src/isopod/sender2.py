import logging
import shlex
import time
from subprocess import DEVNULL, Popen
from threading import Thread
from typing import Optional

from sqlalchemy import select

import isopod
from isopod import db
from isopod.controller import Controller

log = logging.getLogger(__name__)


class Sender(Controller):
    def __init__(self, target_base: str):
        super().__init__()
        self.target_base = target_base

        self._rsync: Optional[Popen] = None
        self._current_path: Optional[str] = None

    def reconcile(self):
        if not self._finalize_rsync():
            return

        if (path := self._get_next_path()) is None:
            log.info("Waiting for next sendable disc")
            return

        args = ["rsync", "--partial", path, f"{self.target_base}/{path}"]
        self._rsync = Popen(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        self._current_path = path
        self._poll_on_finish(self._rsync)
        log.info("Started: %s", shlex.join(args))

    def cleanup(self):
        if self._rsync is not None:
            log.info("Canceling in-flight sync")
            self._rsync.terminate()
            self._rsync.wait()

    def _finalize_rsync(self) -> bool:
        if self._rsync is None:
            return True

        if (returncode := self._rsync.poll()) is None:
            return False

        path = self._current_path
        self._rsync = None
        self._current_path = None
        if returncode == 0:
            self._finalize_rsync_success(path)
        else:
            # TODO: Improved backoff strategy: handle the case of a
            # single ISO being unsendable (e.g. unexpected deletion) and
            # retry exponentially.
            log.info("rsync failed with status %d", returncode)
            self.poll()

        return True

    def _finalize_rsync_success(self, path):
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

    def _poll_on_finish(self, proc: Popen):
        def wait_and_poll():
            proc.wait()
            self.poll()

        Thread(target=wait_and_poll, daemon=True).start()

    def _get_next_path(self):
        with db.Session() as session:
            stmt = select(db.Disc).filter_by(status=db.DiscStatus.SENDABLE)
            disc = session.execute(stmt).scalars().first()
            if disc is not None:
                return disc.path
