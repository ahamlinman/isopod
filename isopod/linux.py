import os
from functools import cache
from hashlib import sha256
from pathlib import Path
from threading import local
from typing import Iterable, Optional

from pyudev import Context, Device, Devices, Enumerator


@cache
def get_boot_id() -> str:
    return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf8").strip()


def _is_fresh_boot() -> bool:
    runtime_dir = os.environ.get("RUNTIME_DIRECTORY", ".")
    bid_file = Path(runtime_dir, "current-boot-id")
    old_bid = bid_file.read_text(encoding="utf8").strip() if bid_file.exists() else None
    if old_bid != get_boot_id():
        bid_file.write_text(get_boot_id(), encoding="utf8")
        return True

    return False


IS_FRESH_BOOT = _is_fresh_boot()


class UdevThreadLocal(local):
    def __init__(self):
        self.context = Context()


UDEV = UdevThreadLocal()


def get_device(path: str) -> Device:
    return Devices.from_device_file(UDEV.context, path)


def get_diskseq(dev: str | Device) -> Optional[str]:
    dev = get_device(dev) if isinstance(dev, str) else dev
    return dev.properties.get("DISKSEQ")


def get_source_hash(dev: str | Device) -> Optional[bytes]:
    dev = get_device(dev) if isinstance(dev, str) else dev
    parts = [get_boot_id(), dev.device_path, get_diskseq(dev)]
    if any(p is None for p in parts):
        return None
    unit_sep = b"\x1f"
    return sha256(unit_sep.join((p.encode("utf-8") for p in parts))).digest()


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
