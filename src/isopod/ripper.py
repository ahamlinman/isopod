import logging

from sqlalchemy import delete

from isopod.store import Disc, DiscStatus, Session

log = logging.getLogger(__name__)


class Controller:
    def __init__(self):
        self._maybe_stale = True

    def reconcile(self):
        if self._maybe_stale:
            self._clear_stale_rips()
            self._maybe_stale = False

    def _clear_stale_rips(self):
        with Session() as session:
            # TODO: Actually delete the old files.
            stmt = delete(Disc).filter_by(status=DiscStatus.RIPPABLE)
            session.execute(stmt)
            session.commit()
