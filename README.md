# Isopod

Isopod is a Linux daemon that watches an optical disc drive, rips the discs
inserted into it, and then rsyncs the resulting ISOs to remote storage in the
background. While it works on any system with the required dependencies, it's
designed for use on a Raspberry Pi with a special E-Ink status display, to
support easy operation by non-technical users.

**For technical reasons, Isopod cannot rip audio CDs or copy-protected media.**
With discs that Isopod _does_ support, you are fully responsible for ensuring
that your use of Isopod complies with all laws, regulations, etc. that you may
be subject to.

Isopod is a personal project created to back up family videos that currently
exist on DVD-Rs, before the discs [rot away](https://en.wikipedia.org/wiki/Disc_rot).
The v1.0.0 release is the version initially shipped (literally, by mail) in
support of this use case, and all continued development activity will be driven
by direct feedback from this production setting. The project will be considered
complete after these discs are transferred, and this repo (TODOs and all) will
remain available with no promise of future maintenance in the hope that it may
inspire future work.

## Requirements

- Linux 5.15+
- Python 3.11+
- libudev
- [GNU ddrescue](https://www.gnu.org/software/ddrescue/)
- [rsync](https://rsync.samba.org/)

Isopod has been tested on Arch Linux ARM and Raspbian 12 ("bookworm").

### Optional E-Ink Status Display

Isopod optionally integrates with the [Adafruit 2.13" E-Ink Bonnet][bonnet] for
Raspberry Pi models with a 2x20 GPIO connector. To enable this support:

- Install the Raspbian (Debian) packages `i2c-tools`, `libgpiod-dev`,
  `python3-libgpiod`, and `python3-pil`.
- [Enable the required Raspberry Pi features with `raspi-config`.][raspi-config]
- Create a virtualenv with the `--system-site-packages` option.
- Install the `adafruit-circuitpython-epd` package into the virtualenv alongside
  Isopod.

[bonnet]: https://www.adafruit.com/product/4687
[raspi-config]: https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi#manual-install-3157124

(For the record, I mostly chose E-Ink based on Adafruit's inventory at the time
of the project. It was probably for the best, though. A "live" display could
have been more interesting, but also harder to set up and use.)

### Terminal Hardware Notes

The "Isopod Terminal" is a Raspberry Pi-based system fitted with the above E-Ink
display, which I've assembled for use by non-technical users (i.e. my parents).

I'm intentionally omitting a formal parts list for the terminal device, to help
actively encourage the reuse of parts you already have or can acquire secondhand
in order to assemble one. In general, the key elements are:

- A Raspberry Pi, optionally with the E-Ink Bonnet linked above
- A USB optical drive
- A **powered** USB hub (to give the drive more current than the Pi can source)
- A way to connect to the Internet (e.g. a Linux-compatible USB WiFi adapter if
  your Pi doesn't have built-in WiFi and you don't want to use Ethernet)

The above being said, I will share two specific hardware-related notes:

- For the Pi models that it fits, [Adafruit's case][case] is perfectly
  compatible with their E-Ink bonnet.
- [Plugable's USB hub][hub] can safely power both the Pi and a USB optical drive
  at the same time, and sticks nicely on the bottom of the Adafruit case with
  some foam tape. The powered hub I originally had on hand could **not** do
  this, and was only safe to use when plugged in separately from the Pi. The
  [eLinux wiki page on this][elinux] is worth a read.

[case]: https://www.adafruit.com/product/2258
[hub]: https://plugable.com/products/usb2-hub4bc
[elinux]: https://elinux.org/RPi_Powered_USB_Hubs
