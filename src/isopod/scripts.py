import logging
import os
import random
import shlex
import signal
import subprocess
import sys
import time
from binascii import hexlify
from subprocess import DEVNULL

import click
from pyudev import Context, Device, Monitor

import isopod.epd.images
import isopod.linux
from isopod.epd.limit import Bucket, TakeBlocked

log = logging.getLogger(__name__)
context_settings = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=context_settings)
def cli():
    """A harness for testing random parts of isopod."""
    pass


@cli.command()
def list():
    """List CD-ROM devices on the system."""
    for dev in isopod.linux.get_cdrom_drives():
        _print_cdrom_info(dev)


@cli.command()
def monitor():
    """Watch udev events on CD-ROM drives and print status updates."""
    context = Context()
    monitor = Monitor.from_netlink(context)
    for dev in iter(monitor.poll, None):
        if isopod.linux.is_cdrom_drive(dev):
            _print_cdrom_info(dev)


def _print_cdrom_info(dev: Device):
    loaded = isopod.linux.is_cdrom_loaded(dev)
    diskseq = isopod.linux.get_diskseq(dev)
    label = isopod.linux.get_fs_label(dev)
    if source_hash := isopod.linux.get_source_hash(dev):
        source_hash = hexlify(source_hash).decode("ascii")
    print(f"{dev.device_node}\t{loaded}\t{diskseq}\t{label}\t{source_hash}")


@cli.group()
def target():
    """Work with the isopod-target container image."""
    pass


TARGET_IMAGE_NAME = "isopod-target:latest"


@target.command(name="build")
@click.option(
    "--image", type=str, default=TARGET_IMAGE_NAME, help="The name of the image"
)
@click.option(
    "--build-root",
    type=click.Path(file_okay=False, dir_okay=True),
    default="./extras/target",
    help="The directory containing the Dockerfile",
)
def target_build(image, build_root):
    """Build the isopod-target image in the local Docker daemon."""
    args = ["docker", "build", f"--tag={image}", build_root]
    log.info("%s", shlex.join(args))
    sys.exit(subprocess.run(args).returncode)


@target.command(name="run")
@click.option(
    "--image", type=str, default=TARGET_IMAGE_NAME, help="The name of the image"
)
@click.option(
    "--address",
    type=str,
    default="127.0.0.1",
    help="The address to bind to on the host",
)
@click.option(
    "--port", type=int, default=11873, help="The port to forward from the host"
)
def target_run(image, address, port):
    """Run the isopod-target image with a persistent volume."""

    args = ["docker", "volume", "inspect", "isopod-target"]
    proc = subprocess.run(args, stdout=DEVNULL, stderr=DEVNULL)
    if proc.returncode != 0:
        args = ["docker", "volume", "create", "isopod-target"]
        log.info(args)
        subprocess.run(args, check=True)

        args = [
            "docker",
            "run",
            "--rm",
            "--volume=isopod-target:/mnt/isopod-target",
            "busybox:latest",
            "chmod",
            "-R",
            "777",
            "/mnt/isopod-target",
        ]
        log.info(args)
        subprocess.run(args, check=True)

    args = [
        "docker",
        "run",
        "--rm",
        "-it",
        "--user=nobody:nogroup",
        "--read-only",
        "--volume=isopod-target:/mnt/isopod-target",
        f"--publish={address}:{port}:{873}",
        image,
    ]
    log.info(args)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    sys.exit(subprocess.run(args).returncode)


@cli.group()
def epd():
    """Work with the Adafruit E-Ink Bonnet."""
    pass


@epd.command(name="list")
def epd_list():
    """List the available named images."""

    names = sorted(
        filename.removesuffix(".png")
        for filename in os.listdir(isopod.epd.images.IMAGE_DIR)
        if filename.endswith(".png")
    )
    for name in names:
        print(name)


@epd.command(name="show")
@click.argument("name")
def epd_show(name):
    """Show the named image on the display."""

    try:
        from isopod.epd.display import DISPLAY
        from isopod.epd.images import load_named_image
    except ImportError as e:
        log.exception("E-Ink display unavailable", exc_info=e)
        sys.exit(1)

    DISPLAY.image(load_named_image(name))
    DISPLAY.display()


@epd.command(name="bucket")
@click.option("--capacity", type=int, help="The capacity of the bucket")
@click.option("--fill-delay", type=float, help="Seconds to wait before adding a token")
@click.option(
    "--burst-delay", type=float, help="Minimum delay in seconds after taking a token"
)
def epd_bucket(capacity, fill_delay, burst_delay):
    bucket = Bucket(capacity=capacity, fill_delay=fill_delay, burst_delay=burst_delay)
    while True:
        try:
            bucket.take()
            log.info("Taken!")
        except TakeBlocked as e:
            log.info("%0.2f seconds remaining", e.seconds_remaining)
            time.sleep(random.random())
