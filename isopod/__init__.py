import sys
import logging

from pyudev import Context, Monitor

from isopod.cdrom import get_drive_status

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-9s %(name)s: %(message)s",
)
log = logging.getLogger("isopod")


def status():
    if len(sys.argv) < 2:
        log.fatal("Need a device to check")
        return 1

    try:
        log.info(get_drive_status(sys.argv[1]))
    except:
        log.exception("Can't read drive status")
        return 1


def monitor():
    context = Context()
    monitor = Monitor.from_netlink(context)
    for d in iter(monitor.poll, None):
        if not "sr" in (d.driver for d in d.ancestors):
            continue

        status = get_drive_status(d.device_node)
        label = d.properties.get("ID_FS_LABEL", None)
        log.info(d.device_node, status, label)
