import logging
import threading
from threading import Thread

log = logging.getLogger(__name__)


class Controller(Thread):
    def __init__(self, target_base: str):
        super().__init__(daemon=True)
        self.target_base = target_base
        self.poke = threading.Event()

    def run(self):
        self.poke.set()

        log.info("Starting control loop")
        while self.poke.wait():
            pass
