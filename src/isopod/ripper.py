import logging
from dataclasses import dataclass
from enum import Enum, auto
from queue import Queue
from threading import Thread

from pyudev import Context, Device, Monitor, MonitorObserver
from sqlalchemy import delete

from isopod.cdrom import DriveStatus, get_cdrom_devices, get_drive_status
from isopod.store import Disc, DiscStatus, Session

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
        self.ready_by_device_path: dict[str, bool] = dict()
        self.udev_context = Context()
        self.udev_monitor = Monitor.from_netlink(self.udev_context)
        self.udev_observer = MonitorObserver(
            self.udev_monitor, callback=self._handle_device_event
        )

    def run(self):
        for dev in get_cdrom_devices():
            if isinstance(path := dev.device_node, str):
                ready = get_drive_status(path) == DriveStatus.DISC_OK
                self.ready_by_device_path[path] = ready
                if ready:
                    log.info("Discovered rippable disc in %s", path)
                    self.events.put(Event(EventKind.DISC_BECAME_READY, path))
                else:
                    log.info("Discovered empty drive %s", path)

        log.info("Starting udev observer")
        self.udev_observer.start()

        while event := self.events.get():
            log.info("Received event %s", event)

    def _handle_device_event(self, dev: Device):
        path = dev.device_node
        last_ready = self.ready_by_device_path[path]
        next_ready = get_drive_status(path) == DriveStatus.DISC_OK
        self.ready_by_device_path[path] = next_ready
        if last_ready and not next_ready:
            log.info("Drive %s is no longer ready", path)
            self.events.put(Event(EventKind.DISC_BECAME_UNREADY, path))
        elif next_ready and not last_ready:
            log.info("Drive %s has become ready", path)
            self.events.put(Event(EventKind.DISC_BECAME_READY, path))


# Create some kind of monitor thread that turns udev events into events that a
# Controller knows how to handle. Start the udev monitor first, and then iterate
# through all known devices to generate their initial events. I guess this
# really implies two layers: one for udev and one for the mapping to the
# controller.
