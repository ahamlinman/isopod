from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Event, Thread, Timer


class Result(ABC):
    pass


class Reconciled(Result):
    pass


@dataclass
class RepollAfter(Result):
    seconds: float


class Controller(ABC):
    def __init__(self, daemon=False):
        self.daemon = daemon
        self._trigger = Event()
        self._canceled = False
        self._repoller = None
        self._thread = Thread(target=self._run, daemon=self.daemon)
        self._thread.start()

    @abstractmethod
    def reconcile(self) -> Result:
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
        try:
            self._run_reconciler()
        except Exception as e:
            self._thread = Thread(target=self._run, daemon=self.daemon)
            self._thread.start()
            raise e

    def _run_reconciler(self):
        while self._trigger.wait():
            if self._repoller is not None:
                self._repoller.cancel()
                self._repoller.join()
                self._repoller = None

            self._trigger.clear()

            if self._canceled:
                self.cleanup()
                return

            match self.reconcile():
                case Reconciled():
                    pass
                case RepollAfter(seconds=seconds):
                    self._repoller = Timer(seconds, self.poll)
                    self._repoller.start()
