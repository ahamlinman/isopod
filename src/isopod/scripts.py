import logging

import click
from pyudev import Context, Device, Monitor

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
        _print_cdrom_info(dev)


@cli.command()
def monitor():
    """Watch udev events on CD-ROM drives and print status updates."""
    context = Context()
    monitor = Monitor.from_netlink(context)
    for dev in iter(monitor.poll, None):
        if isopod.udev.is_cdrom_drive(dev):
            _print_cdrom_info(dev)


def _print_cdrom_info(dev: Device):
    loaded = isopod.udev.is_cdrom_loaded(dev)
    label = isopod.udev.get_fs_label(dev)
    print(f"{dev.device_node}\t{loaded}\t{label}")
