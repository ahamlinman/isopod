import logging

import click
from pyudev import Context, Monitor

import isopod.udev

log = logging.getLogger(__name__)
context_settings = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=context_settings)
def cli():
    """A harness for testing random parts of isopod."""
    pass


@cli.command()
def list():
    """List CD-ROM devices on the system."""
    for dev in isopod.udev.get_cdrom_drives():
        path = dev.device_node
        if isopod.udev.is_cdrom_loaded(dev):
            print(f"{path}\t{isopod.udev.get_fs_label(dev)}")
        else:
            print(path)


@cli.command()
def monitor():
    """Watch udev events on CD-ROM drives and print status updates."""

    context = Context()
    monitor = Monitor.from_netlink(context)
    for d in iter(monitor.poll, None):
        if not "ID_CDROM" in d.properties:
            continue

        loaded = isopod.udev.is_cdrom_loaded(d)
        label = d.properties.get("ID_FS_LABEL", None)
        log.info("%s\t%s\t%s", d.device_node, loaded, label)


@cli.command()
@click.argument("device_path", type=click.Path(exists=True, readable=False))
def status(device_path):
    """Print the status of the CD-ROM device at DEVICE_PATH."""

    try:
        dev = isopod.udev.get_device(device_path)
        log.info(
            "%s %s",
            isopod.udev.is_cdrom_loaded(dev),
            isopod.udev.get_fs_label(dev),
        )
    except:
        log.exception("Can't read drive status")
        return 1
