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
    status: Status
    disc_count: int


class Reporter(Controller):
    def __init__(self, ripper: Ripper):
        super().__init__()
        self._bucket = Bucket(capacity=3, fill_delay=180, burst_delay=30)
        self._ripper = ripper
        self._desired = DisplayState(self._ripper.status, 0)
        self._displayed = DisplayState(Status.UNKNOWN, 0)
        self.poll()

    def reconcile(self) -> Result:
        ripper_status = self._ripper.status
        if ripper_status == Status.UNKNOWN:
            return Reconciled()

        # If the ripper is in a terminal state for a given disc, keep that
        # status on the display even after removing the disc from the drive.
        skip_ripper_update = (
            ripper_status == Status.DRIVE_EMPTY
            and self._desired.status
            in (
                Status.DISC_INVALID,
                Status.LAST_SUCCEEDED,
                Status.LAST_FAILED,
            )
        )
        if not skip_ripper_update:
            self._desired.status = ripper_status

        self._desired.disc_count = _count_sendable_discs()

        if self._displayed == self._desired:
            return Reconciled()

        # Many ripper updates come about through user action, so they deserve
        # the limited refresh cycles more than disc count changes. If the only
        # change is in the disc count, defer it until the bucket is filled to
        # capacity, or until a status update comes in.
        if self._desired.status == self._displayed.status:
            if (delay := self._bucket.seconds_until_full) > 0:
                log.info("Deferring disc count update for %0.2f seconds", delay)
                return RepollAfter(seconds=delay)

        try:
            self._bucket.take()
        except TakeBlocked as e:
            delay = e.seconds_remaining
            log.info("Can refresh display in %0.2f seconds", delay)
            return RepollAfter(seconds=delay)

        name = IMAGE_NAMES_BY_STATUS[self._desired.status]
        img = load_named_image(name)
        draw_pending_discs(img, self._desired.disc_count)
        DISPLAY.image(img)
        DISPLAY.display()
        log.info(
            "Displayed %s image with %d pending disc(s)",
            name,
            self._desired.disc_count,
        )
        self._displayed = DisplayState(self._desired.status, self._desired.disc_count)
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
