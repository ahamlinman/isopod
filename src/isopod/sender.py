import logging
import shlex
from subprocess import DEVNULL, Popen
from threading import Thread
from typing import Optional

from sqlalchemy import select

import isopod
from isopod import db
from isopod.controller import Controller, Reconciled, Result

log = logging.getLogger(__name__)


class Sender(Controller):
    def __init__(self, target_base: str):
        super().__init__()
        self.target_base = target_base

        self._rsync: Optional[Popen] = None
        self._current_path: Optional[str] = None

    def reconcile(self) -> Result:
        if (result := self._reconcile_with_rsync()) is not None:
            return result

        if (disc := self._get_next_disc()) is None:
            log.info("Waiting for next sendable disc")
            return Reconciled()

        args = ["rsync", "--partial", disc.path, f"{self.target_base}/{disc.path}"]
        self._rsync = Popen(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        self._current_disc = disc
        self._poll_on_finish(self._rsync)
        log.info("Started: %s", shlex.join(args))
        return Reconciled()

    def cleanup(self):
        if self._rsync is not None:
            log.info("Canceling in-flight sync")
            self._rsync.terminate()
            self._rsync.wait()

    def _reconcile_with_rsync(self) -> Optional[Result]:
        if self._rsync is None:
            return None

        if (returncode := self._rsync.poll()) is None:
            return Reconciled()

        if returncode == 0:
            self._finalize_rsync_success()
        else:
            # TODO: Improved backoff strategy: handle the case of a
            # single ISO being unsendable (e.g. unexpected deletion) and
            # retry exponentially.
            log.info("rsync failed with status %d", returncode)
            self.poll()

        return None

    def _finalize_rsync_success(self):
        with db.Session() as session:
            if (disc := self._current_disc) is None:
                raise TypeError("missing current disc")

            self._rsync = None
            self._current_disc = None

            disc.status = db.DiscStatus.COMPLETE
            session.merge(disc)
            session.commit()
            log.info("Finished sending %s", disc.path)

            isopod.force_unlink(disc.path)
            session.delete(disc)
            session.commit()
            log.info("Cleaned up %s", disc.path)

    def _poll_on_finish(self, proc: Popen):
        def wait_and_poll():
            proc.wait()
            self.poll()

        Thread(target=wait_and_poll, daemon=True).start()

    def _get_next_disc(self):
        with db.Session() as session:
            stmt = (
                select(db.Disc)
                .filter_by(status=db.DiscStatus.SENDABLE)
                .order_by(db.Disc.send_attempts, db.Disc.last_send_failure)
            )
            return session.execute(stmt).scalars().first()