import logging
from dataclasses import dataclass
from enum import Enum, auto
from queue import Queue
from threading import Thread

from pyudev import Context, Device, Monitor, MonitorObserver

import isopod.udev

log = logging.getLogger(__name__)


class EventKind(Enum):
    DISC_BECAME_READY = auto()
    DISC_BECAME_UNREADY = auto()
    RIP_SUCCEEDED = auto()
    RIP_FAILED = auto()


@dataclass
class Event:
    kind: EventKind
    device_path: str


class Controller(Thread):
    def __init__(self):
        super().__init__()
        self.events: Queue[Event] = Queue()
        self.disc_label_by_device: dict[str, str] = dict()
        self.udev_context = Context()
        self.udev_monitor = Monitor.from_netlink(self.udev_context)
        self.udev_observer = MonitorObserver(
            self.udev_monitor, callback=self._refresh_device
        )

    def run(self):
        log.info("Initializing CD-ROM device monitoring")
        self.udev_observer.start()
        for dev in isopod.udev.get_cdrom_drives():
            self._refresh_device(dev)

        log.info("Starting controller")
        while event := self.events.get():
            log.debug("Received event %s", event)

    def _refresh_device(self, dev: Device):
        path = dev.device_node
        last_label = self.disc_label_by_device.get(path)
        last_ready = last_label is not None
        next_ready = isopod.udev.is_cdrom_loaded(dev)

        if last_ready and not next_ready:
            log.debug("Disc removed from %s", path)
            del self.disc_label_by_device[path]
            self.events.put(Event(EventKind.DISC_BECAME_UNREADY, path))

        if not next_ready:
            return

        next_label = isopod.udev.get_fs_label(dev)
        if next_label is None:
            log.warn("Disc in %s has no label; tracking may be inaccurate", path)
            next_label = ""

        self.disc_label_by_device[path] = next_label
        if next_ready and not last_ready:
            log.debug("Disc inserted into %s", path)
            self.events.put(Event(EventKind.DISC_BECAME_READY, path))
        elif last_ready and next_ready and last_label != next_label:
            log.debug("Disc replaced in %s", path)
            self.events.put(Event(EventKind.DISC_BECAME_UNREADY, path))
            self.events.put(Event(EventKind.DISC_BECAME_READY, path))
