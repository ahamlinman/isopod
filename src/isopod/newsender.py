import threading
from subprocess import Popen
from threading import Thread
from typing import Optional

from isopod import db


class Controller(Thread):
    def __init__(self):
        super().__init__()
        self._trigger = threading.Event()

        self._canceled = False

        self._rsync: Optional[Popen] = None

    def run(self):
        self._trigger.set()
        while self._trigger.wait():
            self._trigger.clear()

            if self._canceled:
                if self._rsync is not None:
                    self._rsync.terminate()
                    self._rsync.wait()
                return

    def cancel(self):
        self._canceled = True
        self._trigger.set()
