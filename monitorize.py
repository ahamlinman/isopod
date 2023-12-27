#!/usr/bin/env python3

import os
from fcntl import ioctl
from pyudev import Context, Monitor

CDROM_DRIVE_STATUS = 0x5326
CDSL_NONE = 2147483646


def main():
    context = Context()
    monitor = Monitor.from_netlink(context)
    for d in iter(monitor.poll, None):
        if not "sr" in (d.driver for d in d.ancestors):
            continue

        fd = os.open(d.device_node, os.O_RDONLY | os.O_NONBLOCK)
        result = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_NONE)
        os.close(fd)
        print(result)


if __name__ == "__main__":
    main()
