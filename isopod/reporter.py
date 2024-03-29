import logging

from isopod.ripper import Ripper

log = logging.getLogger(__name__)


class NullReporter:
    def __init__(self, _: Ripper):
        pass

    def poll(self):
        pass

    def cancel(self):
        pass

    def join(self):
        pass


try:
    from isopod.epd.reporter import Reporter as EPDReporter

    Reporter = EPDReporter
except ImportError:
    Reporter = NullReporter
