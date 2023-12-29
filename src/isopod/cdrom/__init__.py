import os
from enum import Enum
from fcntl import ioctl

from isopod.cdrom.constants import (
    CDROM_DRIVE_STATUS,
    CDS_DISC_OK,
    CDS_DRIVE_NOT_READY,
    CDS_NO_DISC,
    CDS_NO_INFO,
    CDS_TRAY_OPEN,
    CDSL_NONE,
)


class DriveStatus(Enum):
    NO_INFO = CDS_NO_INFO
    NO_DISC = CDS_NO_DISC
    TRAY_OPEN = CDS_TRAY_OPEN
    DRIVE_NOT_READY = CDS_DRIVE_NOT_READY
    DISC_OK = CDS_DISC_OK


def get_drive_status(device_node: str) -> DriveStatus:
    fd = os.open(device_node, os.O_RDONLY | os.O_NONBLOCK)
    try:
        result = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_NONE)
        return DriveStatus(result)
    finally:
        os.close(fd)
