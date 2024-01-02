import logging
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
        self._last_source = isopod.linux.get_source_hash(self.device_path)
        with db.Session() as session:
            stmt = (
                select(func.count())
                .select_from(db.Disc)
                .filter_by(status=db.DiscStatus.SENDABLE, source_hash=self._last_source)
            )
            if session.execute(stmt).scalar_one() == int(0):
                self._last_source = None

        self._udev_monitor = Monitor.from_netlink(isopod.linux.UDEV.context)
        self._udev_observer = MonitorObserver(
            self._udev_monitor, lambda *_: self.poll()
        )

    def reconcile(self) -> Result:
        return Reconciled()

    def cleanup(self):
        self._udev_observer.stop()
