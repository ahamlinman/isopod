import logging
import threading
import time
from dataclasses import dataclass
from queue import Queue
from subprocess import DEVNULL, Popen
from threading import Thread
from typing import Callable, Optional

from pyudev import Context, Device, Monitor, MonitorObserver

import isopod
import isopod.linux
from isopod import db

log = logging.getLogger(__name__)


class DriveState:
    pass


@dataclass
class DrivePreloaded(DriveState):
    pass


@dataclass
class DriveLoaded(DriveState):
    device: Device

    def __eq__(self, other):
        if not isinstance(other, DriveLoaded):
            return False

        self_seq = isopod.linux.get_diskseq(self.device)
        other_seq = isopod.linux.get_diskseq(other.device)
        return self.device == other.device and self_seq == other_seq


@dataclass
class DriveUnloaded(DriveState):
    pass


class Controller(Thread):
    def __init__(self, device_path: str, on_rip_success: Callable):
        super().__init__(daemon=True)

        self.device_path = device_path
        self.on_rip_success = on_rip_success

        self.next_states: Queue[DriveState] = Queue()
        self.ripper: Optional[Ripper] = None

        self.udev_context = Context()
        self.udev_monitor = Monitor.from_netlink(self.udev_context)
        self.udev_observer = MonitorObserver(
            self.udev_monitor, callback=self._handle_device_event
        )

    def run(self):
        self.device = isopod.linux.get_device(self.device_path)
        init_source_hash = isopod.linux.get_source_hash(self.device)
        with db.Session() as session:
            if (
                session.query(db.Disc)
                .filter_by(status=db.DiscStatus.SENDABLE, source_hash=init_source_hash)
                .count()
                > 0
            ):
                self.state = DrivePreloaded()
            else:
                self.state = DriveUnloaded()

        self.udev_observer.start()
        self._handle_device_event(self.device)
        log.info("Started device monitor")

        while next_state := self.next_states.get():
            if isinstance(self.state, DrivePreloaded):
                log.info("Current disc is already ripped and ready to send")
                self.state = next_state
                continue
            elif self.state == next_state:
                continue

            self.state = next_state
            log.info("Drive state changed: %s", self.state)

            if self.ripper is not None:
                log.info("Finalizing previous ripper")
                self.ripper.terminate()
                self.ripper.join()
                self.ripper = None

            if isinstance(self.state, DriveLoaded):
                log.info("Starting new ripper")
                self.device = self.state.device
                dst = str(time.time_ns())
                if label := isopod.linux.get_fs_label(self.device):
                    dst += f"_{label}"
                dst += ".iso"
                self.ripper = Ripper(self.device, dst, self.on_rip_success)
                self.ripper.start()

    def _handle_device_event(self, dev: Device):
        if dev == self.device:
            if isopod.linux.is_cdrom_loaded(dev):
                self.next_states.put(DriveLoaded(dev))
            else:
                self.next_states.put(DriveUnloaded())


class Ripper(Thread):
    def __init__(self, src_device: Device, dst: str, on_rip_success: Callable):
        super().__init__(daemon=False)
        self.src_device = src_device
        self.dst = dst
        self.on_rip_success = on_rip_success
        self.trigger = threading.Event()
        self.terminal = False
        self.terminating = False

    def run(self):
        # TODO: Check for minimum available space in the working directory.

        with db.Session() as session:
            disc = db.Disc(path=self.dst, status=db.DiscStatus.RIPPABLE)
            session.add(disc)
            session.commit()

        args = [
            "ddrescue",
            "--retry-passes=2",
            "--timeout=300",
            self.src_device.device_node,
            self.dst,
        ]
        self.proc = Popen(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        Thread(target=self._wait_and_poke, daemon=True).start()
        log.info("Started ripper process: %s", args)

        while self.trigger.wait():
            if self.terminal and not self.terminating:
                self.proc.terminate()
                self.terminating = True

            if self.proc.poll() is None:
                continue

            log.info("Ripper exited with status %d", self.proc.returncode)
            self.terminal = True
            self.terminating = True

            if self.proc.returncode != 0:
                with db.Session() as session:
                    isopod.force_unlink(self.dst)
                    session.delete(disc)
                    session.commit()
                    return

            with db.Session() as session:
                disc.status = db.DiscStatus.SENDABLE
                disc.source_hash = isopod.linux.get_source_hash(self.src_device)
                session.merge(disc)
                session.commit()

            self.on_rip_success()
            return

    def terminate(self):
        if not self.terminal:
            self.terminal = True
            self.trigger.set()

    def _wait_and_poke(self):
        self.proc.wait()
        self.trigger.set()
