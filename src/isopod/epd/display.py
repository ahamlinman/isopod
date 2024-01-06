import board
import busio
import digitalio
from adafruit_epd.ssd1680 import Adafruit_SSD1680

DISPLAY = Adafruit_SSD1680(
    122,
    250,
    busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO),
    cs_pin=digitalio.DigitalInOut(board.CE0),
    dc_pin=digitalio.DigitalInOut(board.D22),
    sramcs_pin=None,
    rst_pin=digitalio.DigitalInOut(board.D27),
    busy_pin=digitalio.DigitalInOut(board.D17),
)
DISPLAY.rotation = 1
