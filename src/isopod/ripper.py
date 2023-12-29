import logging
from dataclasses import dataclass
from enum import Enum, auto
from queue import Queue
from threading import Thread

from sqlalchemy import delete

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
