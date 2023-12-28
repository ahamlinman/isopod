#!/usr/bin/env python3

# A minimal test harness that combines udev monitoring of a CD/DVD drive with
# the ioctl call from main.c. This is the sketch for how the Cloud Copycat can
# figure out when to start copying a disc.
#
# The next big thing would be to find the name of the disc, so we can use it to
# name the resulting ISO.

from cdrom import get_drive_status, DriveStatus
from pyudev import Context, Monitor


def main():
    context = Context()
    monitor = Monitor.from_netlink(context)
    for d in iter(monitor.poll, None):
        if not "sr" in (d.driver for d in d.ancestors):
            continue

        status = get_drive_status(d.device_node)
        if status == DriveStatus.DISC_OK:
            print(status, d.properties.get("ID_FS_LABEL", None))
        else:
            print(status)


if __name__ == "__main__":
    main()
