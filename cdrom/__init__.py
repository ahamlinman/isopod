from contextlib import contextmanager
from enum import Enum
from fcntl import ioctl
import os

from . import constants as _c


class DriveStatus(Enum):
    NO_INFO = _c.CDS_NO_INFO
    NO_DISC = _c.CDS_NO_DISC
    TRAY_OPEN = _c.CDS_TRAY_OPEN
    DRIVE_NOT_READY = _c.CDS_DRIVE_NOT_READY
    DISC_OK = _c.CDS_DISC_OK


def get_drive_status(device_node: str) -> DriveStatus:
    with _open_raw(device_node, os.O_RDONLY | os.O_NONBLOCK) as fd:
        result = ioctl(fd, _c.CDROM_DRIVE_STATUS, _c.CDSL_NONE)
        return DriveStatus(result)


@contextmanager
def _open_raw(path: str, flags: int):
    fd = os.open(path, flags)
    try:
        yield fd
    finally:
        os.close(fd)
