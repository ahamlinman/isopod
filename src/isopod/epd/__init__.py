import logging
import os.path
from functools import cache

import board
import busio
import digitalio
from adafruit_epd.ssd1680 import Adafruit_SSD1680
from PIL import Image

from isopod.controller import Controller, Reconciled, RepollAfter
from isopod.epd.limit import Bucket, TakeBlocked
from isopod.ripper import Ripper, Status

# create the spi device and pins we will need
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D22)
srcs = None
rst = digitalio.DigitalInOut(board.D27)
busy = digitalio.DigitalInOut(board.D17)

display = Adafruit_SSD1680(
    122,
    250,
    spi,
    cs_pin=ecs,
    dc_pin=dc,
    sramcs_pin=srcs,
    rst_pin=rst,
    busy_pin=busy,
)
display.rotation = 1

log = logging.getLogger(__name__)
image_dir = os.path.dirname(__file__)


def display_named_image(name: str):
    display.image(_load_named_image(name))
    display.display()


@cache
def _load_named_image(name: str):
    image_path = os.path.join(image_dir, f"{name}.png")
    return Image.open(image_path).convert("1").convert("L")


class Display(Controller):
    def __init__(self, ripper: Ripper):
        super().__init__(daemon=True)
        self._bucket = Bucket(capacity=2, fill_delay=180, burst_delay=30)
        self._ripper = ripper
        self._last_status = None
        self.poll()

    def reconcile(self):
        status = self._ripper.status
        if status == Status.INITIALIZING or status == self._last_status:
            return Reconciled()

        try:
            self._bucket.take()
        except TakeBlocked as e:
            delay = e.seconds_remaining
            log.info("Waiting %0.2f seconds to refresh display", delay)
            return RepollAfter(seconds=delay)

        images_by_status = {
            Status.INITIALIZED: "insert",
            Status.RIPPING: "copying",
            Status.DISC_INVALID: "unreadable",
            Status.LAST_SUCCEEDED: "success",
            Status.LAST_FAILED: "failure",
        }
        name = images_by_status[status]
        display_named_image(name)
        log.info("Displayed %s image", name)
        self._last_status = status
        return Reconciled()

    def cleanup(self):
        pass
