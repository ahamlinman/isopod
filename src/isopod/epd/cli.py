import isopod.logging

isopod.logging.configure()

import logging
import os
import sys

import click

import isopod.epd.images

log = logging.getLogger(__name__)
context_settings = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=context_settings)
def cli():
    """Work with the Adafruit E-Ink Bonnet on an Isopod terminal device."""
    pass


@cli.command()
def list():
    """List the available named images."""

    names = sorted(
        filename.removesuffix(".png")
        for filename in os.listdir(isopod.epd.images.IMAGE_DIR)
        if filename.endswith(".png")
    )
    for name in names:
        print(name)


@cli.command()
@click.argument("name")
def show(name):
    """Show the named image on the display."""

    try:
        from isopod.epd.display import DISPLAY
        from isopod.epd.images import load_named_image
    except ImportError as e:
        log.exception("Missing E-Ink display support", exc_info=e)
        sys.exit(1)

    DISPLAY.image(load_named_image(name))
    DISPLAY.display()
