import logging

from sqlalchemy import func, select

from isopod import db
from isopod.controller import Controller, Reconciled, RepollAfter, Result
from isopod.epd.display import DISPLAY
from isopod.epd.images import draw_pending_discs, load_named_image
from isopod.epd.limit import Bucket, TakeBlocked
from isopod.ripper import Ripper, Status

log = logging.getLogger(__name__)

IMAGE_NAMES_BY_STATUS = {
    Status.DRIVE_EMPTY: "insert",
    Status.WAITING_FOR_SPACE: "wait",
    Status.RIPPING: "copying",
    Status.DISC_INVALID: "unreadable",
    Status.LAST_SUCCEEDED: "success",
    Status.LAST_FAILED: "failure",
}


class Reporter(Controller):
    def __init__(self, ripper: Ripper):
        super().__init__()
        self._bucket = Bucket(capacity=3, fill_delay=180, burst_delay=30)
        self._ripper = ripper
        self._desired_status = self._ripper.status
        self._displayed_status = None
        self.poll()

    def reconcile(self):
        current_status = self._ripper.status
        if current_status == Status.UNKNOWN:
            return Reconciled()

        if current_status == Status.DRIVE_EMPTY and self._desired_status in (
            Status.DISC_INVALID,
            Status.LAST_SUCCEEDED,
            Status.LAST_FAILED,
        ):
            pass  # Emptying the drive isn't important enough to update the display.
        else:
            self._desired_status = current_status

        if self._displayed_status == self._desired_status:
            return Reconciled()

        try:
            self._bucket.take()
        except TakeBlocked as e:
            delay = e.seconds_remaining
            log.info("Can refresh display in %0.2f seconds", delay)
            return RepollAfter(seconds=delay)

        name = IMAGE_NAMES_BY_STATUS[self._desired_status]
        img = load_named_image(name)
        draw_pending_discs(img, _count_sendable_discs())
        DISPLAY.image(img)
        DISPLAY.display()
        log.info("Displayed %s image", name)
        self._displayed_status = self._desired_status
        return Reconciled()

    def cleanup(self):
        self.reconcile()


def _count_sendable_discs():
    with db.Session() as session:
        stmt = (
            select(func.count())
            .select_from(db.Disc)
            .filter_by(status=db.DiscStatus.SENDABLE)
        )
        return session.execute(stmt).scalar_one()
