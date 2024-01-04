import os.path

import board
import busio
import digitalio
from adafruit_epd.ssd1680 import Adafruit_SSD1680
from PIL import Image

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

image_dir = os.path.dirname(__file__)


def display_named_image(name: str):
    image_path = os.path.join(image_dir, f"{name}.png")
    image = Image.open(image_path).convert("1").convert("L")
    display.image(image)
    display.display()
