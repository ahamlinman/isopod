import logging
from dataclasses import dataclass

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


@dataclass
class DisplayState:
    ripper_status: Status
    sendable_count: int


class Reporter(Controller):
    def __init__(self, ripper: Ripper):
        super().__init__()
        self._bucket = Bucket(capacity=3, fill_delay=180, burst_delay=30)
        self._ripper = ripper
        self._desired = DisplayState(self._ripper.status, 0)
        self._displayed = DisplayState(Status.UNKNOWN, 0)
        self.poll()

    def reconcile(self):
        ripper_status = self._ripper.status
        if ripper_status == Status.UNKNOWN:
            log.info("Deferring update; ripper status unknown")
            return Reconciled()  # Wait until we know for sure which image to show.

        self._desired.sendable_count = _count_sendable_discs()

        # Don't wipe out useful status messages just because the drive was emptied.
        skip_ripper_update = (
            ripper_status == Status.DRIVE_EMPTY
            and self._desired.ripper_status
            in (
                Status.DISC_INVALID,
                Status.LAST_SUCCEEDED,
                Status.LAST_FAILED,
            )
        )
        if not skip_ripper_update:
            self._desired.ripper_status = ripper_status

        if self._displayed == self._desired:
            log.info("Desired %s matches displayed %s", self._desired, self._displayed)
            return Reconciled()  # We're already up to date.

        if self._desired.ripper_status == self._displayed.ripper_status:
            # If the only change is in the pending disc count, defer this update
            # until the token bucket is filled to capacity, or until we need to
            # update the ripper status.
            if (delay := self._bucket.seconds_until_full) > 0:
                log.info("Deferring sendable disc update for %0.2f seconds", delay)
                return RepollAfter(seconds=delay)

        try:
            self._bucket.take()
        except TakeBlocked as e:
            delay = e.seconds_remaining
            log.info("Can refresh display in %0.2f seconds", delay)
            return RepollAfter(seconds=delay)

        name = IMAGE_NAMES_BY_STATUS[self._desired.ripper_status]
        img = load_named_image(name)
        draw_pending_discs(img, self._desired.sendable_count)
        DISPLAY.image(img)
        DISPLAY.display()
        log.info(
            "Displayed %s image with %d pending disc(s)",
            name,
            self._desired.sendable_count,
        )
        self._displayed = self._desired
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
