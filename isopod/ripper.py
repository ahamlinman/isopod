import io
import logging
import os.path
import shlex
import shutil
import time
from enum import Enum, auto
from subprocess import DEVNULL, PIPE, Popen, TimeoutExpired
from threading import Thread
from typing import Optional

from pyudev import Device, Monitor, MonitorObserver
from sqlalchemy import select

import isopod.linux
import isopod.os
from isopod import db
from isopod.controller import Controller, EventSet, Reconciled, RepollAfter, Result

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
        journal_ddrescue_output: bool,
    ):
        super().__init__()
        self.device_path = device_path
        self.min_free_bytes = min_free_bytes
        self.event_log_dir = event_log_dir
        self.journal_ddrescue_output = journal_ddrescue_output

        self.on_status_change = EventSet()

        self._ripper = None

        monitor = Monitor.from_netlink(isopod.linux.UDEV.context)
        self._udev_observer = MonitorObserver(monitor, callback=self._update_device)
        self._device = isopod.linux.get_device(self.device_path)
        self._udev_observer.start()
        self._device = isopod.linux.get_device(self.device_path)

        current_source_hash = isopod.linux.get_source_hash(self._device)
        with db.Session() as session:
            stmt = (
                select(db.Disc.source_hash)
                .filter_by(source_hash=current_source_hash)
                .where(db.Disc.status != db.DiscStatus.RIPPABLE)
                .limit(1)
            )
            if (found := session.execute(stmt).scalar_one_or_none()) is not None:
                self._status = Status.LAST_SUCCEEDED
                self._last_source_hash = found
            elif isopod.linux.is_fresh_boot():
                self._status = Status.DRIVE_EMPTY
                self._last_source_hash = current_source_hash
            else:
                self._status = Status.UNKNOWN
                self._last_source_hash = None

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
            return Reconciled()

        if not loaded:
            self.status = Status.DRIVE_EMPTY
            return Reconciled()

        if not self._can_read_disc_volume_descriptor():
            log.warn("Quick read check failed, refusing to rip disc")
            self.status = Status.DISC_INVALID
            return Reconciled()

        if (result := self._check_min_free_space()) is not None:
            return result

        self._last_source_hash = source_hash
        iso_filename = self._get_iso_filename()
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

        output = self._get_ripper_output()
        args = [
            "ddrescue",
            "--idirect",
            "--sector-size=2048",
            "--timeout=30m",
            f"--log-events={os.path.join(self.event_log_dir, f'{iso_filename}.log')}",
            self._device.device_node,
            iso_filename,
        ]
        try:
            self._ripper = Popen(args, stdin=DEVNULL, stdout=output, stderr=output)
        finally:
            if not isinstance(output, int):
                output.close()

        Thread(target=self._poll_after_rip, daemon=True).start()
        log.info("Running: %s", shlex.join(args))
        self.status = Status.RIPPING
        return Reconciled()

    def _can_read_disc_volume_descriptor(self) -> bool:
        # See https://wiki.osdev.org/ISO_9660#Volume_Descriptors.
        SECTOR_SIZE = 2048
        assert self._device.device_node is not None
        with open(self._device.device_node, "rb") as disc:
            try:
                disc.seek(16 * SECTOR_SIZE)
                disc.read(SECTOR_SIZE)
                return True
            except:
                return False

    def _check_min_free_space(self) -> Optional[Result]:
        assert self._device.device_node is not None
        with open(self._device.device_node, "rb") as blk:
            disc_size = blk.seek(0, io.SEEK_END)
            need_free = disc_size + self.min_free_bytes

        df = shutil.disk_usage(".")
        if need_free > df.total:
            log.error(
                "Disc too large; need %d bytes free, have %d total in filesystem",
                need_free,
                df.total,
            )
            self.status = Status.LAST_FAILED
            return Reconciled()

        if df.free < need_free:
            log.info("%d bytes free, waiting for at least %d", df.free, need_free)
            self.status = Status.WAITING_FOR_SPACE
            return RepollAfter(seconds=60)

        return None

    def _get_iso_filename(self):
        name = str(time.time_ns())
        if label := isopod.linux.get_fs_label(self._device):
            name += f"_{label}"
        return f"{name}.iso"

    def _get_ripper_output(self):
        if not self.journal_ddrescue_output:
            return DEVNULL

        # TODO: The goal is to compress and rotate ddrescue's logs to limit
        # their size without racy copy + truncate logic, regardless of how long
        # ddrescue runs for. Namespaced systemd journals work out of the box on
        # Debian bookworm, and I knew enough about them in advance to hack this
        # together quickly. They're awkward to use, though, on top of the other
        # baggage associated with journald.
        #
        # I don't consider it a priority to rework this, but wouldn't recommend
        # taking inspiration from it. There are surely better answers for this
        # outside the systemd ecosystem.
        args = [
            "systemd-run",
            "--pipe",
            "--quiet",
            "--collect",
            "--slice-inherit",
            f"--property=LogNamespace=isopod-ripper",
            "systemd-cat",
            "-t",
            "ddrescue",
        ]
        proc = Popen(args, stdin=PIPE, stdout=DEVNULL, stderr=DEVNULL)
        assert proc.stdin is not None
        return proc.stdin

    def _poll_after_rip(self):
        ripper = self._ripper
        if ripper is not None:
            ripper.wait()
            self.poll()

    def cleanup(self):
        self._udev_observer.stop()

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
            self.on_status_change.dispatch()
