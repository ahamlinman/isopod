import logging
from subprocess import Popen
from typing import Callable

from pyudev import Monitor, MonitorObserver
from sqlalchemy import func, select

import isopod.linux
from isopod import db
from isopod.controller import Controller, Reconciled, Result

log = logging.getLogger(__name__)


class Ripper(Controller):
    def __init__(self, device_path: str, min_free_bytes: int, on_rip_success: Callable):
        super().__init__()
        self.device_path = device_path
        self.min_free_bytes = min_free_bytes
        self.on_rip_success = on_rip_success

        self._rip_proc = None
        self._rip_source = isopod.linux.get_source_hash(self.device_path)
        with db.Session() as session:
            stmt = (
                select(func.count())
                .select_from(db.Disc)
                .filter_by(status=db.DiscStatus.SENDABLE, source_hash=self._rip_source)
            )
            if session.execute(stmt).scalar_one() == int(0):
                self._rip_source = None

        self._udev_monitor = Monitor.from_netlink(isopod.linux.UDEV.context)
        self._udev_observer = MonitorObserver(
            self._udev_monitor, lambda *_: self.poll()
        )
        self._udev_observer.start()

    def _never_called(self):
        # TODO: Remove this; I'm only using it for type hinting purposes.
        self._rip_proc = Popen(["true"])

    def reconcile(self) -> Result:
        if self._rip_proc is not None:
            match self._rip_proc.poll():
                case None:
                    return Reconciled()
                case 0:
                    self._finalize_rip_success()
                case _:
                    self._finalize_rip_failure()

        return Reconciled()

    def cleanup(self):
        if self._rip_proc is not None:
            log.info("Waiting for in-flight rip to finish")
            self._rip_proc.wait()

        self._udev_observer.stop()

    def _finalize_rip_success(self):
        self._rip_proc = None

    def _finalize_rip_failure(self):
        self._rip_proc = None
