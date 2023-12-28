from enum import Enum
from fcntl import ioctl
import os

import cdrom.constants as _c


class DriveStatus(Enum):
    NO_INFO = _c.CDS_NO_INFO
    NO_DISC = _c.CDS_NO_DISC
    TRAY_OPEN = _c.CDS_TRAY_OPEN
    DRIVE_NOT_READY = _c.CDS_DRIVE_NOT_READY
    DISC_OK = _c.CDS_DISC_OK


def get_drive_status(device_node: str) -> DriveStatus:
    fd = os.open(device_node, os.O_RDONLY | os.O_NONBLOCK)
    result = ioctl(fd, _c.CDROM_DRIVE_STATUS, _c.CDSL_NONE)
    os.close(fd)
    return DriveStatus(result)
