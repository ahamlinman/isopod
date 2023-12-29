from sqlalchemy import delete, select

from isopod.store import Disc, DiscStatus, Session


class Controller:
    def __init__(self):
        self._clear_stale_rips()

    def reconcile(self):
        pass

    def _clear_stale_rips(self):
        with Session() as session:
            # TODO: Actually delete the old files.
            stmt = delete(Disc).filter_by(status=DiscStatus.RIPPABLE)
            session.execute(stmt)
            session.commit()
