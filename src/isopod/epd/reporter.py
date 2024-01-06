import logging

from isopod.controller import Controller, Reconciled, RepollAfter
from isopod.epd.display import display_named_image
from isopod.epd.limit import Bucket, TakeBlocked
from isopod.ripper import Ripper, Status

log = logging.getLogger(__name__)


class Reporter(Controller):
    def __init__(self, ripper: Ripper):
        super().__init__(daemon=True)
        self._bucket = Bucket(capacity=3, fill_delay=180, burst_delay=30)
        self._ripper = ripper
        self._last_status = None
        self.poll()

    def reconcile(self):
        status = self._ripper.status
        if status in (Status.UNKNOWN, self._last_status):
            return Reconciled()

        if status == Status.DRIVE_EMPTY and self._last_status in (
            Status.DISC_INVALID,
            Status.LAST_SUCCEEDED,
            Status.LAST_FAILED,
        ):
            # Emptying the drive isn't important enough to update the display.
            return Reconciled()

        try:
            self._bucket.take()
        except TakeBlocked as e:
            delay = e.seconds_remaining
            log.info("Waiting %0.2f seconds to refresh display", delay)
            return RepollAfter(seconds=delay)

        images_by_status = {
            Status.DRIVE_EMPTY: "insert",
            Status.WAITING_FOR_SPACE: "wait",
            Status.RIPPING: "copying",
            Status.DISC_INVALID: "unreadable",
            Status.LAST_SUCCEEDED: "success",
            Status.LAST_FAILED: "failure",
        }
        name = images_by_status[status]
        display_named_image(name)
        log.info("Displayed %s image", name)
        self._last_status = status
        return Reconciled()

    def cleanup(self):
        pass
