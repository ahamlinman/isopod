import logging
from dataclasses import dataclass
from queue import Queue
from threading import Thread
from typing import Optional

from pyudev import Context, Device, Monitor, MonitorObserver

import isopod.udev

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
    def __init__(self, device_path: str):
        super().__init__(daemon=True)

        self.device = isopod.udev.get_device(device_path)
        self.state = DriveUnloaded()
        self.next_states: Queue[DriveState] = Queue()

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

            if isinstance(self.state, DriveLoaded):
                log.info("Would start a new rip process")
            else:
                log.info("Would kill any ongoing rip process")

    def _handle_device_event(self, dev: Device):
        if dev == self.device:
            if isopod.udev.is_cdrom_loaded(dev):
                label = isopod.udev.get_fs_label(dev)
                self.next_states.put(DriveLoaded(label))
            else:
                self.next_states.put(DriveUnloaded())


# def _rip_device(self, device_path: str):
#     args = [
#         "ddrescue",
#         "--retry-passes=2",
#         "--timeout=300",
#         device_path,
#         f"isopod-{time.strftime('%F-%H-%M-%S')}.iso",
#     ]
#     log.debug("Ripping with: %s", args)
#     proc = Popen(args, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
#     _spawn_popen_waiter(self, device_path, proc)
#     self.rip_popen_by_device[device_path] = proc
#     log.info("Successfully started ripping %s", device_path)


# def _spawn_popen_waiter(ctl: Dispatcher, device_path: str, proc: Popen):
#     def wait_for_process():
#         if (returncode := proc.wait()) == 0:
#             ctl.events.put(Dispatch(DispatchKind.RIP_SUCCEEDED, device_path))
#         else:
#             log.warn("Rip process exited with code %d", returncode)
#             ctl.events.put(Dispatch(DispatchKind.RIP_FAILED, device_path))

#     Thread(target=wait_for_process, daemon=True).start()
