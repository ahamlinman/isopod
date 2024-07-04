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

I created Isopod to back up family videos that previously existed solely on
DVD-R discs, before those discs [rotted away](https://en.wikipedia.org/wiki/Disc_rot).
The v1.0.0 release was the version that I shipped (literally, by mail) to carry
out this effort, which was ultimately successful. I consider Isopod a finished
project (even with its outstanding TODOs), and am keeping it available to the
public with no promise of future maintenance in the hope that it may inspire
future work.

> Arrakis teaches the attitude of the knife—chopping off what's incomplete and
> saying: "Now, it's complete because it's ended here."
>
>   — from "Collected Sayings of Muad'Dib" by the Princess Irulan
>
>   <small>(actually from _Dune_ by Frank Herbert)</small>

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

(I mostly chose E-Ink based on Adafruit's inventory at the time of the project.
A "live" display could have been more interesting, but also harder to set up
and use, so this unintentional choice may have been for the best.)

### Terminal Hardware Notes

The "Isopod Terminal" is a Raspberry Pi-based system fitted with the above E-Ink
display, which provides a simple user experience for ripping a series of discs.

I'm intentionally omitting a formal parts list for the terminal device, to help
actively encourage the reuse of parts you already have or can acquire secondhand
in order to assemble one. In general, the key elements are:

- A Raspberry Pi, optionally with the E-Ink Bonnet linked above
- A USB optical drive
- A **powered** USB hub (to give the drive more current than the Pi can source)
- A way to connect to the Internet (e.g. a Linux-compatible USB WiFi adapter if
  your Pi doesn't have built-in WiFi and you don't want to use Ethernet)

That said, I'll share two specific hardware-related notes:

- For the Pi models that it fits, [Adafruit's case][case] is perfectly
  compatible with their E-Ink Bonnet.
- [Plugable's USB hub][hub] can safely power both the Pi and a USB optical drive
  at the same time, and sticks nicely on the bottom of the Adafruit case with
  some foam tape. The powered hub I originally had on hand could **not** do
  this, and was only safe to use when plugged in separately from the Pi. The
  [eLinux wiki page on this][elinux] is worth a read.

[case]: https://www.adafruit.com/product/2258
[hub]: https://plugable.com/products/usb2-hub4bc
[elinux]: https://elinux.org/RPi_Powered_USB_Hubs
