import logging
import os
import os.path
import threading
import time
from dataclasses import dataclass
from queue import Queue
from subprocess import DEVNULL, Popen
from threading import Thread
from typing import Optional

from pyudev import Context, Device, Monitor, MonitorObserver

import isopod.store
import isopod.udev
from isopod.store import DiscStatus

log = logging.getLogger(__name__)


class DriveState:
    pass


@dataclass
class DriveLoaded(DriveState):
    label: Optional[str]


@dataclass
class DriveUnloaded(DriveState):
    pass


class Controller(Thread):
    def __init__(self, device_path: str, staging_dir: str):
        super().__init__(daemon=True)

        self.device = isopod.udev.get_device(device_path)
        self.staging_dir = staging_dir
        self.state = DriveUnloaded()
        self.next_states: Queue[DriveState] = Queue()
        self.ripper: Optional[Ripper] = None

        self.udev_context = Context()
        self.udev_monitor = Monitor.from_netlink(self.udev_context)
        self.udev_observer = MonitorObserver(
            self.udev_monitor, callback=self._handle_device_event
        )

    def run(self):
        self.udev_observer.start()
        self._handle_device_event(self.device)

        while next_state := self.next_states.get():
            if self.state == next_state:
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
                src = self.device.device_node
                filename = str(time.time()).replace(".", "")
                if self.state.label:
                    filename += f"_{self.state.label}"
                filename += ".iso"
                dst = os.path.join(self.staging_dir, filename)
                self.ripper = Ripper(src, dst)
                self.ripper.start()

    def _handle_device_event(self, dev: Device):
        if dev == self.device:
            if isopod.udev.is_cdrom_loaded(dev):
                label = isopod.udev.get_fs_label(dev)
                self.next_states.put(DriveLoaded(label))
            else:
                self.next_states.put(DriveUnloaded())


class Ripper(Thread):
    def __init__(self, src: str, dst: str):
        super().__init__()
        self.poke = threading.Event()
        self.src = src
        self.dst = dst
        self.terminal = False
        self.terminating = False

    def run(self):
        with isopod.store.Session() as session:
            disc = isopod.store.Disc(path=self.dst, status=DiscStatus.RIPPABLE)
            session.add(disc)
            session.commit()

        args = [
            "ddrescue",
            "--retry-passes=2",
            "--timeout=300",
            self.src,
            self.dst,
        ]
        self.proc = Popen(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        Thread(target=self._wait_and_poke, daemon=True).start()
        log.info("Started ripper process: %s", args)

        while self.poke.wait():
            if self.terminal and not self.terminating:
                self.proc.terminate()
                self.terminating = True

            if self.proc.poll() is None:
                continue

            log.info("Ripper exited with status %d", self.proc.returncode)
            self.terminal = True
            self.terminating = True

            if self.proc.returncode == 0:
                with isopod.store.Session() as session:
                    disc.status = DiscStatus.SENDABLE
                    session.merge(disc)
                    session.commit()
            else:
                try:
                    os.unlink(self.dst)
                except FileNotFoundError:
                    pass
                with isopod.store.Session() as session:
                    session.delete(disc)
                    session.commit()

            return

    def terminate(self):
        if not self.terminal:
            self.terminal = True
            self.poke.set()

    def _wait_and_poke(self):
        self.proc.wait()
        self.poke.set()
