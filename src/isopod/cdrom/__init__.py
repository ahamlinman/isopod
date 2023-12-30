import os
from enum import Enum
from fcntl import ioctl
from typing import Iterable, Optional

from pyudev import Context, Device, DeviceNotFoundError, Devices, Enumerator

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


def get_cdrom_devices() -> Iterable[Device]:
    return Enumerator(Context()).match_property("ID_CDROM", "1")


def get_cdrom_device_paths() -> list[str]:
    return [
        d.device_node for d in Enumerator(Context()).match_property("ID_CDROM", "1")
    ]


def get_drive_status(device_path: str) -> DriveStatus:
    fd = os.open(device_path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        result = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_NONE)
        return DriveStatus(result)
    finally:
        os.close(fd)


def get_fs_label(device_path: str) -> Optional[str]:
    try:
        # TODO: Is a shared Context safe across threads?
        dev = Devices.from_device_file(Context(), device_path)
        return dev.properties.get("ID_FS_LABEL", None)
    except DeviceNotFoundError:
        return None
