import logging
import threading
from threading import Thread

from sqlalchemy import select

from isopod.store import Disc, DiscStatus, Session

log = logging.getLogger(__name__)


class Controller(Thread):
    def __init__(self, target_base: str):
        super().__init__(daemon=True)
        self.target_base = target_base
        self.poke = threading.Event()

    def run(self):
        self.poke.set()
        while self.poke.wait():
            self.poke.clear()

            if (path := self._get_next_path()) is None:
                log.info("Waiting for next sendable ISO")
                continue

            log.info("Sending %s", path)

    def _get_next_path(self):
        with Session() as session:
            stmt = select(Disc).filter_by(status=DiscStatus.SENDABLE)
            disc = session.execute(stmt).scalars().first()
            if disc is not None:
                return disc.path
