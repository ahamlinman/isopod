import logging

import click
from pyudev import Context, Monitor

from isopod.cdrom import get_cdrom_device_paths, get_drive_status, get_fs_label

log = logging.getLogger(__name__)
context_settings = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=context_settings)
def list():
    """List all CD-ROM devices on the system."""
    print(get_cdrom_device_paths())


@click.command(context_settings=context_settings)
@click.argument("device_path", type=click.Path(exists=True))
def status(device_path):
    """Print the status of the CD-ROM drive at DEVICE_PATH as seen by isopod.cdrom."""

    try:
        log.info("%s %s", get_drive_status(device_path), get_fs_label(device_path))
    except:
        log.exception("Can't read drive status")
        return 1


@click.command(context_settings=context_settings)
def monitor():
    """Watch for udev events on CD-ROM drives and print the status as seen by isopod.cdrom."""

    context = Context()
    monitor = Monitor.from_netlink(context)
    for d in iter(monitor.poll, None):
        if not "ID_CDROM" in d.properties:
            continue

        status = get_drive_status(d.device_node)
        label = d.properties.get("ID_FS_LABEL", None)
        log.info("%s %s %s", d.device_node, status, label)
