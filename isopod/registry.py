import logging
from dataclasses import dataclass
from enum import Enum, auto

from sqlalchemy import create_engine, text

# Work around SQLAlchemy adding their own handler for echo=True, even though we
# already have one at the root.
logging.getLogger("sqlalchemy.engine.Engine").addHandler(logging.NullHandler())


class DiscStatus(Enum):
    RIPPABLE = auto()
    SENDABLE = auto()
    COMPLETE = auto()


@dataclass
class Disc:
    name: str
    status: DiscStatus


class Registry:
    def __init__(self, db_path: str):
        # TODO: Remove echo=True after initial debugging.
        self._engine = create_engine(f"sqlite+pysqlite:///{db_path}", echo=True)
        with self._engine.begin() as conn:
            conn.execute(
                text("CREATE TABLE IF NOT EXISTS isopod (hello INTEGER PRIMARY KEY)")
            )
