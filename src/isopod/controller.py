from abc import ABC, abstractmethod
from threading import Event, Thread


class Controller(ABC):
    def __init__(self):
        self._thread = Thread(target=self._run)
        self._trigger = Event()
        self._canceled = False
        self._thread.start()

    @abstractmethod
    def reconcile(self):
        pass

    @abstractmethod
    def cleanup(self):
        pass

    def poll(self):
        self._trigger.set()

    def cancel(self):
        self._canceled = True
        self._trigger.set()

    @property
    def canceled(self):
        return self._canceled

    def _run(self):
        while self._trigger.wait():
            self._trigger.clear()
            if not self._canceled:
                self.reconcile()
            else:
                self.cleanup()
                return
