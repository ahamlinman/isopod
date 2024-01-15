from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Event, Thread, Timer
from typing import Callable


class Result(ABC):
    """Base class for values returned by :meth:`Controller.reconcile`."""

    pass


class Reconciled(Result):
    """The controller will only reconcile again after the next explicit poll."""

    pass


@dataclass
class RepollAfter(Result):
    """
    The controller will reconcile again after the next explicit poll, or after
    the provided number of seconds have passed with no other poll attempt.
    """

    seconds: float


class Controller(ABC):
    """
    A representation of logic that incrementally drives the actual state of the
    world toward a desired state upon request.
    """

    # TODO: My first-pass implementation of controllers calls subclass methods
    # in a per-instance background thread. There are probably better approaches,
    # but I have no concrete need to explore them right now.

    def __init__(self):
        self._trigger = Event()
        self._canceled = False
        self._repoller = None
        self._thread = Thread(target=self._run, daemon=False)
        self._thread.start()

    @abstractmethod
    def reconcile(self) -> Result:
        """
        Analyze the current state of the world, and perform all work required to
        converge it with some desired state of the world. To be implemented by
        subclasses and invoked by the controller.

        A :class:`Controller` invokes `reconcile` in a separate thread shortly
        after one or more calls to :meth:`poll`, never making more than one
        concurrent call to the same reconciler. Reconcilers should return
        quickly, and manage threads or subprocesses for long-running work. To
        sleep for a period of time, use :class:`RepollAfter` rather than
        sleeping directly.
        """

        pass

    @abstractmethod
    def cleanup(self):
        """
        Cancel any asynchronous work that this controller is responsible for
        managing, and wait for it to finish before returning. To be implemented
        by subclasses and invoked by the controller.
        """

        pass

    def poll(self):
        """Schedule a call to the reconciler in the background shortly in the future."""
        self._trigger.set()

    def cancel(self):
        """Request that the controller cancel any pending work."""
        self._canceled = True
        self._trigger.set()

    @property
    def canceled(self):
        return self._canceled

    def join(self):
        """Wait for the controller to finish pending work after cancellation."""
        self._thread.join()

    def _run(self):
        # TODO: The Isopod daemon installs a global hook to exit the process on
        # unhandled exceptions in threads; otherwise, Python merely logs the
        # exception and terminates the thread. A more robust version of this
        # abstraction wouldn't rely on a global hook to avoid silent breakage.
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


class EventSet:
    def __init__(self):
        self.handlers: set[Callable] = set()

    def add(self, fn: Callable):
        self.handlers |= {fn}

    def dispatch(self):
        for fn in self.handlers:
            fn()
