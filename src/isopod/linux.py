from pathlib import Path
from threading import local
from typing import Iterable, Optional

from pyudev import Context, Device, Devices, Enumerator


def get_boot_id() -> str:
    return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()


class UdevThreadLocal(local):
    def __init__(self):
        self.context = Context()


UDEV = UdevThreadLocal()


def get_device(path: str) -> Device:
    return Devices.from_device_file(UDEV.context, path)


def get_diskseq(dev: str | Device) -> Optional[str]:
    dev = get_device(dev) if isinstance(dev, str) else dev
    return dev.properties.get("DISKSEQ")


def get_fs_label(dev: str | Device) -> Optional[str]:
    dev = get_device(dev) if isinstance(dev, str) else dev
    return dev.properties.get("ID_FS_LABEL")


def get_cdrom_drives() -> Iterable[Device]:
    return Enumerator(UDEV.context).match_property("ID_CDROM", "1")


def is_cdrom_drive(dev: str | Device) -> bool:
    dev = get_device(dev) if isinstance(dev, str) else dev
    return dev.properties.get("ID_CDROM") == "1"


def is_cdrom_loaded(dev: str | Device) -> bool:
    dev = get_device(dev) if isinstance(dev, str) else dev
    return dev.properties.get("ID_CDROM_MEDIA") == "1"
