from enum import Enum
from threading import local
from typing import Iterable, Optional

from pyudev import Context, Device, DeviceNotFoundError, Devices, Enumerator


class LocalContext(local):
    def __init__(self):
        self.ctx = Context()


CTX = LocalContext()


def get_drives() -> Iterable[Device]:
    return Enumerator(CTX.ctx).match_property("ID_CDROM", "1")


# old stuff follows


class DriveStatus(Enum):
    NO_DISC = 0
    DISC_OK = 1


def get_cdrom_devices() -> Iterable[Device]:
    return Enumerator(Context()).match_property("ID_CDROM", "1")


def get_drive_status(device_path: str) -> DriveStatus:
    dev = Devices.from_device_file(Context(), device_path)
    if dev.properties.get("ID_CDROM_MEDIA") == "1":
        return DriveStatus.DISC_OK
    else:
        return DriveStatus.NO_DISC


def get_fs_label(device_path: str) -> Optional[str]:
    try:
        # TODO: Is a shared Context safe across threads?
        dev = Devices.from_device_file(Context(), device_path)
        return dev.properties.get("ID_FS_LABEL", None)
    except DeviceNotFoundError:
        return None
