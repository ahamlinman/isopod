import logging
from dataclasses import dataclass
from enum import Enum, auto
from queue import Queue
from threading import Thread

from pyudev import Context, Device, Monitor, MonitorObserver

import isopod.udev

log = logging.getLogger(__name__)


class EventKind(Enum):
    DISC_LOADED = auto()
    DISC_UNLOADED = auto()
    RIP_SUCCEEDED = auto()
    RIP_FAILED = auto()


@dataclass
class Event:
    kind: EventKind
    device_path: str


class Controller(Thread):
    def __init__(self):
        super().__init__(daemon=True)
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
        while evt := self.events.get():
            match evt.kind:
                case EventKind.DISC_LOADED:
                    log.info("%s became ready", evt.device_path)
                case EventKind.DISC_UNLOADED:
                    log.info("%s became unready", evt.device_path)
                case EventKind.RIP_SUCCEEDED:
                    log.info("%s successfully ripped", evt.device_path)
                case EventKind.RIP_FAILED:
                    log.info("%s failed to rip", evt.device_path)

    def _refresh_device(self, dev: Device):
        path = dev.device_node
        last_label = self.disc_label_by_device.get(path)
        last_loaded = last_label is not None
        next_loaded = isopod.udev.is_cdrom_loaded(dev)

        if last_loaded and not next_loaded:
            del self.disc_label_by_device[path]
            self.events.put(Event(EventKind.DISC_UNLOADED, path))

        if not next_loaded:
            return

        next_label = isopod.udev.get_fs_label(dev)
        if next_label is None:
            log.warn("Disc in %s has no label; tracking may be inaccurate", path)
            next_label = ""

        self.disc_label_by_device[path] = next_label
        if not last_loaded:
            self.events.put(Event(EventKind.DISC_LOADED, path))
        elif last_loaded and last_label != next_label:
            self.events.put(Event(EventKind.DISC_UNLOADED, path))
            self.events.put(Event(EventKind.DISC_LOADED, path))
