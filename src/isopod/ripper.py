import io
import logging
import os.path
import shlex
import shutil
import time
from enum import Enum, auto
from subprocess import DEVNULL, Popen, TimeoutExpired
from threading import Thread
from typing import Callable, Optional

from pyudev import Device, Monitor, MonitorObserver
from sqlalchemy import select

import isopod.linux
import isopod.os
from isopod import db
from isopod.controller import Controller, Reconciled, RepollAfter, Result

log = logging.getLogger(__name__)


class Status(Enum):
    UNKNOWN = auto()
    DRIVE_EMPTY = auto()
    WAITING_FOR_SPACE = auto()
    RIPPING = auto()
    DISC_INVALID = auto()
    LAST_SUCCEEDED = auto()
    LAST_FAILED = auto()


class Ripper(Controller):
    def __init__(
        self,
        /,
        device_path: str,
        min_free_bytes: int,
        event_log_dir: str,
    ):
        super().__init__()
        self.device_path = device_path
        self.min_free_bytes = min_free_bytes
        self.event_log_dir = event_log_dir

        self._status = Status.UNKNOWN
        self._watchers: set[Callable] = set()

        self._ripper = None
        with db.Session() as session:
            stmt = (
                select(db.Disc.source_hash)
                .filter_by(
                    status=db.DiscStatus.SENDABLE,
                    source_hash=isopod.linux.get_source_hash(device_path),
                )
                .limit(1)
            )
            self._last_source_hash = session.execute(stmt).scalar_one_or_none()

        monitor = Monitor.from_netlink(isopod.linux.UDEV.context)
        self._udev_observer = MonitorObserver(monitor, callback=self._update_device)
        self._device = isopod.linux.get_device(self.device_path)
        self._udev_observer.start()
        self._device = isopod.linux.get_device(self.device_path)
        self.poll()

    def _update_device(self, dev: Device):
        if dev != self._device:
            return

        if oldseq := isopod.linux.get_diskseq(self._device):
            newseq = isopod.linux.get_diskseq(dev)
            if newseq and int(oldseq) > int(newseq):
                return

        self._device = dev
        self.poll()

    def reconcile(self) -> Result:
        source_hash = isopod.linux.get_source_hash(self._device)
        loaded = isopod.linux.is_cdrom_loaded(self._device)

        if self._ripper is not None:
            if source_hash != self._last_source_hash or not loaded:
                self._ripper.terminate()

            match self._ripper.poll():
                case None:
                    return Reconciled()
                case 0:
                    self._finalize_rip_success()
                case returncode:
                    self._finalize_rip_failure(returncode)

        if source_hash == self._last_source_hash:
            if self.status == Status.UNKNOWN:
                self.status = Status.LAST_SUCCEEDED
            return Reconciled()

        if not loaded:
            self.status = Status.DRIVE_EMPTY
            return Reconciled()

        with open(self._device.device_node, "rb") as disc:  # type: ignore
            try:
                # https://wiki.osdev.org/ISO_9660#Volume_Descriptors
                disc.seek(16 * 2048)
                disc.read(2048)
            except:
                log.warn("Quick read check failed, refusing to rip disc")
                self.status = Status.DISC_INVALID
                return Reconciled()

        if (result := self._check_min_free_space()) is not None:
            self.status = Status.WAITING_FOR_SPACE
            return result

        iso_filename = str(time.time_ns())
        if label := isopod.linux.get_fs_label(self._device):
            iso_filename += f"_{label}"
        iso_filename += ".iso"

        event_log_path = os.path.join(self.event_log_dir, f"{iso_filename}.log")

        log.info(
            "Ready to rip %s (diskseq=%s) to %s",
            self._device.device_node,
            isopod.linux.get_diskseq(self._device),
            iso_filename,
        )

        with db.Session() as session:
            disc = db.Disc(
                path=iso_filename,
                status=db.DiscStatus.RIPPABLE,
                source_hash=source_hash,
            )
            session.add(disc)
            session.commit()

        self._last_source_hash = source_hash
        args = [
            "ddrescue",
            "--idirect",
            "--sector-size=2048",
            f"--log-events={event_log_path}",
            self._device.device_node,
            iso_filename,
        ]
        self._ripper = Popen(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        Thread(target=self._poll_after_rip, daemon=True).start()
        log.info("Running: %s", shlex.join(args))
        self.status = Status.RIPPING
        return Reconciled()

    def _check_min_free_space(self) -> Optional[Result]:
        with open(self._device.device_node, "rb") as blk:  # type: ignore
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
        if self._ripper is None:
            raise TypeError("missing rip process")

        self._ripper.wait()
        self.poll()

    def cleanup(self):
        self._udev_observer.stop()
        self._wait_for_last_rip()

    def _wait_for_last_rip(self):
        if self._ripper is None:
            return

        log.info("Waiting for in-flight rip to finish")
        disc_changed = False
        while self._try_wait(proc=self._ripper, timeout=2) is None:
            device = isopod.linux.get_device(self.device_path)
            loaded = isopod.linux.is_cdrom_loaded(device)
            source_hash = isopod.linux.get_source_hash(device)
            if self._last_source_hash != source_hash or not loaded:
                disc_changed = True
                self._ripper.terminate()
                break

        returncode = self._ripper.wait()
        if returncode == 0 and not disc_changed:
            self._finalize_rip_success()
        else:
            self._finalize_rip_failure(returncode)

    @staticmethod
    def _try_wait(proc: Popen, timeout: int):
        try:
            return proc.wait(timeout=timeout)
        except TimeoutExpired:
            return None

    def _finalize_rip_success(self):
        with db.Session() as session:
            stmt = select(db.Disc).filter_by(
                status=db.DiscStatus.RIPPABLE, source_hash=self._last_source_hash
            )
            disc = session.execute(stmt).scalar_one()
            disc.status = db.DiscStatus.SENDABLE
            session.commit()

        log.info("Rip succeeded")
        self._ripper = None
        self.status = Status.LAST_SUCCEEDED

    def _finalize_rip_failure(self, returncode: int):
        with db.Session() as session:
            stmt = select(db.Disc).filter_by(
                status=db.DiscStatus.RIPPABLE, source_hash=self._last_source_hash
            )
            if disc := session.execute(stmt).scalar_one_or_none():
                isopod.os.force_unlink(disc.path)
                session.delete(disc)
                session.commit()

        log.info("Rip failed with status %d", returncode)
        self._ripper = None
        self.status = Status.LAST_FAILED

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value: Status):
        if self._status != value:
            self._status = value
            for watcher in self._watchers:
                watcher()

    def notify(self, watcher: Callable):
        self._watchers |= {watcher}
        watcher()
