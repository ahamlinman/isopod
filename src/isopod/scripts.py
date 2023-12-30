import logging

import click
from pyudev import Context, Monitor

from isopod.cdrom import get_cdrom_devices, get_drive_status, get_fs_label

log = logging.getLogger(__name__)
context_settings = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=context_settings)
def cli():
    """A harness for testing random parts of isopod."""
    pass


@cli.command()
def list():
    """List CD-ROM devices on the system."""
    for dev in get_cdrom_devices():
        print(dev.device_node)


@cli.command()
def monitor():
    """Watch udev events on CD-ROM drives and print status updates."""

    context = Context()
    monitor = Monitor.from_netlink(context)
    for d in iter(monitor.poll, None):
        if not "ID_CDROM" in d.properties:
            continue

        status = get_drive_status(d.device_node)
        label = d.properties.get("ID_FS_LABEL", None)
        log.info("%s %s %s", d.device_node, status, label)


@cli.command()
@click.argument("device_path", type=click.Path(exists=True))
def status(device_path):
    """Print the status of the CD-ROM device at DEVICE_PATH."""

    try:
        log.info("%s %s", get_drive_status(device_path), get_fs_label(device_path))
    except:
        log.exception("Can't read drive status")
        return 1
