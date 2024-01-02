import datetime
import logging
import shlex
from subprocess import DEVNULL, Popen
from threading import Thread
from typing import Optional

from sqlalchemy import select

import isopod
from isopod import db
from isopod.controller import Controller, Reconciled, RepollAfter, Result

log = logging.getLogger(__name__)


class Sender(Controller):
    def __init__(self, target_base: str):
        super().__init__()
        self.target_base = target_base

        self._rsync = None
        self._current_disc = None

        self.poll()

    def reconcile(self) -> Result:
        if self._rsync is not None:
            match self._rsync.poll():
                case None:
                    return Reconciled()
                case 0:
                    self._finalize_rsync_success()
                case _:
                    self._finalize_rsync_failure()

        if (disc := self._get_next_disc()) is None:
            log.info("Waiting for next sendable disc")
            return Reconciled()

        if disc.next_send_attempt is not None:
            delay = disc.next_send_attempt - datetime.datetime.utcnow()
            delay_sec = delay.total_seconds()
            if delay_sec > 0:
                log.info("Will retry after %0.1f second(s)", delay_sec)
                return RepollAfter(seconds=delay_sec)

        args = ["rsync", "--partial", disc.path, f"{self.target_base}/{disc.path}"]
        self._rsync = Popen(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        self._current_disc = disc
        Thread(target=self._poll_after_rsync, daemon=True).start()
        log.info("Started: %s", shlex.join(args))
        return Reconciled()

    def cleanup(self):
        if self._rsync is not None:
            log.info("Canceling in-flight send")
            self._rsync.terminate()
            self._rsync.wait()

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

    def _finalize_rsync_failure(self):
        with db.Session() as session:
            if (disc := self._current_disc) is None:
                raise TypeError("missing current disc")

            self._rsync = None
            self._current_disc = None

            log.info("Failed to send %s", disc.path)
            disc.send_errors += 1
            retry_base_sec = 5
            retry_max_sec = 300
            disc.next_send_attempt = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=min(
                    retry_max_sec, retry_base_sec * (2 ** (disc.send_errors - 1))
                )
            )
            session.merge(disc)
            session.commit()

    def _get_next_disc(self):
        with db.Session() as session:
            stmt = (
                select(db.Disc)
                .filter_by(status=db.DiscStatus.SENDABLE)
                .order_by(db.Disc.next_send_attempt.asc())
            )
            return session.execute(stmt).scalars().first()

    def _poll_after_rsync(self):
        if self._rsync is None:
            raise TypeError("missing rsync process")

        self._rsync.wait()
        self.poll()
