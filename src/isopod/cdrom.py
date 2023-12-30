from threading import local
from typing import Iterable, Optional

from pyudev import Context, Device, Devices, Enumerator


class LocalContext(local):
    def __init__(self):
        self.ctx = Context()


CTX = LocalContext()


def get_drives() -> Iterable[Device]:
    return Enumerator(CTX.ctx).match_property("ID_CDROM", "1")


def get_device(path: str) -> Device:
    return Devices.from_device_file(CTX.ctx, path)


def is_drive_loaded(dev: str | Device) -> bool:
    dev = get_device(dev) if isinstance(dev, str) else dev
    return dev.properties.get("ID_CDROM_MEDIA") == "1"


def get_label(dev: str | Device) -> Optional[str]:
    dev = get_device(dev) if isinstance(dev, str) else dev
    return dev.properties.get("ID_FS_LABEL")
