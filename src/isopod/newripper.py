import io
import logging
import shlex
import shutil
import time
from subprocess import DEVNULL, Popen
from threading import Thread
from typing import Callable, Optional

from pyudev import Monitor, MonitorObserver
from sqlalchemy import func, select

import isopod.linux
from isopod import db
from isopod.controller import Controller, Reconciled, RepollAfter, Result

log = logging.getLogger(__name__)


class Ripper(Controller):
    def __init__(self, device_path: str, min_free_bytes: int, on_rip_success: Callable):
        super().__init__()
        self.device_path = device_path
        self.min_free_bytes = min_free_bytes
        self.on_rip_success = on_rip_success

        self._rip_proc = None
        self._rip_source = isopod.linux.get_source_hash(self.device_path)
        self._rip_disc = None
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
        self.poll()

    def reconcile(self) -> Result:
        device = isopod.linux.get_device(self.device_path)
        if not isopod.linux.is_cdrom_loaded(device):
            if self._rip_proc is not None:
                log.info("Terminating ripper process due to disc removal")
                self._rip_proc.terminate()
            return Reconciled()

        if self._rip_proc is not None:
            match self._rip_proc.poll():
                case None:
                    return Reconciled()
                case 0:
                    log.info("Rip succeeded")
                    self._finalize_rip_success()
                case returncode:
                    log.info("Rip failed with code %d", returncode)
                    self._finalize_rip_failure()

        source_hash = isopod.linux.get_source_hash(device)
        if source_hash == self._rip_source:
            return Reconciled()

        if (result := self._check_min_free_space()) is not None:
            return result

        path = str(time.time_ns())
        if label := isopod.linux.get_fs_label(device):
            path += f"_{label}"
        path += ".iso"
        log.info(
            "Ready to rip %s (diskseq=%s) to %s",
            self.device_path,
            isopod.linux.get_diskseq(device),
            path,
        )

        with db.Session() as session:
            self._rip_disc = db.Disc(path=path, status=db.DiscStatus.RIPPABLE)
            session.add(self._rip_disc)
            session.commit()

        args = ["ddrescue", "--retry-passes=2", "--timeout=300", self.device_path, path]
        self._rip_proc = Popen(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        self._rip_source = source_hash
        Thread(target=self._poll_after_rip, daemon=True).start()
        log.info("Running: %s", shlex.join(args))
        return Reconciled()

    def cleanup(self):
        self._udev_observer.stop()
        if self._rip_proc is not None:
            log.info("Waiting for in-flight rip to finish")
            self._rip_proc.wait()

    def _finalize_rip_success(self):
        if (disc := self._rip_disc) is None:
            raise TypeError("missing disc")
        if (rip_source := self._rip_source) is None:
            raise TypeError("missing rip source")

        with db.Session() as session:
            disc.status = db.DiscStatus.SENDABLE
            disc.source_hash = rip_source
            session.merge(disc)
            session.commit()

        self._rip_proc = None
        self._rip_source = None
        self._rip_disc = None
        self.on_rip_success()

    def _finalize_rip_failure(self):
        if (disc := self._rip_disc) is None:
            raise TypeError("missing disc")

        with db.Session() as session:
            isopod.force_unlink(disc.path)
            session.delete(disc)
            session.commit()

        self._rip_proc = None
        self._rip_source = None
        self._rip_disc = None

    def _check_min_free_space(self) -> Optional[Result]:
        with open(self.device_path, "rb") as blk:
            disc_size = blk.seek(0, io.SEEK_END)
            need_free = disc_size + self.min_free_bytes

        df = shutil.disk_usage(".")
        if need_free > df.total:
            log.error(
                "Disc too large; need %d bytes free, have %d total in filesystem",
                need_free,
                df.total,
            )
            return Reconciled()

        if df.free < need_free:
            log.info("%d bytes free, waiting for at least %d", df.free, need_free)
            return RepollAfter(seconds=30)

        return None

    def _poll_after_rip(self):
        if self._rip_proc is None:
            raise TypeError("missing rip process")

        self._rip_proc.wait()
        self.poll()
