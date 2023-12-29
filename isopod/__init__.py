from pyudev import Context, Monitor

from isopod.cdrom import get_drive_status


def monitor():
    context = Context()
    monitor = Monitor.from_netlink(context)
    for d in iter(monitor.poll, None):
        if not "sr" in (d.driver for d in d.ancestors):
            continue

        status = get_drive_status(d.device_node)
        label = d.properties.get("ID_FS_LABEL", None)
        print(d.device_node, status, label)
